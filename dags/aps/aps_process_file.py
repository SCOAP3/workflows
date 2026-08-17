import json
import logging
import xml.etree.ElementTree as ET
from copy import deepcopy

import pendulum
from airflow.sdk import Param, dag, get_current_context, task
from aps.parser import APSParser, APSXMLParser
from aps.repository import APSRepository
from common.enhancer import Enhancer
from common.enricher import Enricher
from common.exceptions import EmptyOutputFromPreviousTask
from common.notification_service import FailedDagNotifier
from common.scoap3_s3 import Scoap3Repository
from common.utils import create_or_update_article, upload_json_to_s3
from inspire_utils.record import get_value

logger = logging.getLogger("airflow.task")


def parse_aps(data):
    parser = APSParser()
    parsed = parser.parse(data)
    return parsed


def enhance_aps(parsed_file):
    return Enhancer()("APS", parsed_file)


def enrich_aps(enhanced_file):
    return Enricher()(enhanced_file)


def merge_authors_with_xml_authors(
    parsed_json, parsed_xml, fail_if_author_count_not_equal=True
):
    if fail_if_author_count_not_equal and len(parsed_json["authors"]) != len(
        parsed_xml["authors"]
    ):
        raise ValueError("Number of authors in JSON and XML do not match")

    xml_authors_by_full_name = {}
    for xml_author in parsed_xml.get("authors", []):
        full_name = xml_author.get("full_name")
        if full_name and full_name not in xml_authors_by_full_name:
            xml_authors_by_full_name[full_name] = xml_author

    merged_json = deepcopy(parsed_json)

    for json_author in merged_json.get("authors", []):
        full_name = json_author.get("full_name")
        matched_xml_author = xml_authors_by_full_name.get(full_name)
        if not matched_xml_author:
            logger.error(
                "Could not match API author full_name '%s' to XML author list during ORCID merge.",
                full_name,
            )
            continue

        xml_orcid = matched_xml_author.get("orcid")
        if xml_orcid:
            json_author["orcid"] = xml_orcid

    return merged_json


def add_data_availability(parsed_json, parsed_xml):
    parsed_json["data_availability"] = parsed_xml.get("data_availability")
    return parsed_json

def populate_files_aps(parsed_file):
    if "dois" not in parsed_file:
        return parsed_file

    doi = get_value(parsed_file, "dois.value[0]")
    logger.info("Populating files for doi: %s", doi)

    files = {
        "pdf": f"https://harvest.aps.org/v2/journals/articles/{doi}",
        "xml": f"https://harvest.aps.org/v2/journals/articles/{doi}",
    }
    s3_scoap3_client = Scoap3Repository()
    downloaded_files = s3_scoap3_client.download_files_for_aps(files, prefix=doi)
    parsed_file["files"] = downloaded_files
    logger.info("Files populated: %s", parsed_file["files"])
    return parsed_file

@dag(
    on_failure_callback=FailedDagNotifier(),
    schedule=None,
    start_date=pendulum.today("UTC").add(days=-1),
    tags=["process", "aps"],
    params={
        "fail_if_author_count_not_equal": Param(True, type="boolean"),
    },
)
def aps_process_file():
    s3_client = APSRepository()

    @task()
    def parse(**kwargs):
        if "params" in kwargs and "article" in kwargs["params"]:
            article = json.loads(kwargs["params"]["article"])
            return parse_aps(article)

    @task()
    def enhance(parsed_file):
        if not parsed_file:
            raise EmptyOutputFromPreviousTask("parse")
        return enhance_aps(parsed_file)

    @task()
    def enrich(enhanced_file):
        if not enhanced_file:
            raise EmptyOutputFromPreviousTask("enhance")
        return enrich_aps(enhanced_file)

    @task()
    def populate_files(parsed_file):
        return populate_files_aps(parsed_file)


    @task()
    def parse_xml(parsed_file):
        xml_path = parsed_file.get("files", {}).get("xml")
        if not xml_path:
            logger.warning("No XML file found for parsing.")
            return {}

        s3_scoap3_client = Scoap3Repository()
        xml_bytes = s3_scoap3_client.get_by_id(xml_path).getvalue()
        xml_content = xml_bytes.decode("utf-8")

        logger.info("Parsing XML file: %s", xml_path)
        parser = APSXMLParser()
        parsed = parser.parse(ET.fromstring(xml_content))
        return parsed

    @task(task_id="merge_authors_with_xml_authors")
    def task_merge_authors_with_xml_authors(parsed_json, parsed_xml):
        if not parsed_xml:
            logger.warning("No parsed XML data available for author ORCID merge.")
            return parsed_json
        ctx = get_current_context()
        return merge_authors_with_xml_authors(
            parsed_json,
            parsed_xml,
            fail_if_author_count_not_equal=ctx["params"][
                "fail_if_author_count_not_equal"
            ],
        )

    @task(task_id="add_data_availability")
    def task_add_data_availability(parsed_json, parsed_xml):
        if not parsed_xml:
            logger.warning("No parsed XML data available for adding data availability.")
            return parsed_json
        return add_data_availability(parsed_json, parsed_xml)

    @task()
    def save_to_s3(complete_file):
        upload_json_to_s3(json_record=complete_file, repo=s3_client)

    @task()
    def create_or_update(complete_file):
        create_or_update_article(complete_file)

    parsed_file = parse()
    enhanced_file = enhance(parsed_file)
    enhanced_file_with_files = populate_files(enhanced_file)
    enriched_file = enrich(enhanced_file_with_files)
    parsed_xml = parse_xml(enriched_file)
    merged_authors_file = task_merge_authors_with_xml_authors(enriched_file, parsed_xml)
    complete_file = task_add_data_availability(merged_authors_file, parsed_xml)
    save_to_s3(complete_file)
    create_or_update(complete_file)


dag_for_aps_files_processing = aps_process_file()
