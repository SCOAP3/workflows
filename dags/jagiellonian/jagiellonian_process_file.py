import logging

import pendulum
from airflow.sdk import dag, task
from common.enhancer import Enhancer
from common.enricher import Enricher
from common.notification_service import FailedDagNotifier
from common.scoap3_s3 import Scoap3Repository
from common.utils import create_or_update_article, upload_json_to_s3
from jagiellonian.parser import JagiellonianParser
from jagiellonian.repository import JagiellonianRepository

logger = logging.getLogger("airflow.task")
JAGIELLONIAN_REPO = JagiellonianRepository()
SCOAP3_REPO = Scoap3Repository()


@dag(
    on_failure_callback=FailedDagNotifier(),
    schedule=None,
    start_date=pendulum.today("UTC").add(days=-1),
    tags=["process", "jagiellonian"],
)
def jagiellonian_process_file():
    @task(task_id="jagiellonian-parse")
    def parse(**kwargs):
        if "params" in kwargs and "article" in kwargs["params"]:
            article = kwargs["params"]["article"]

            if (
                isinstance(article, dict)
                and isinstance(article.get("dois"), list)
                and article.get("dois")
                and isinstance(article["dois"][0], dict)
                and article["dois"][0].get("value")
            ):
                return article

            parsed = JagiellonianParser().parse(article)

            if "dois" not in parsed:
                raise ValueError("DOI not found in metadata")

            return parsed

    @task(task_id="jagiellonian-populate-files")
    def populate_files(parsed_file, repo=SCOAP3_REPO):
        if "files" not in parsed_file:
            return parsed_file

        doi = parsed_file.get("dois")[0]["value"]
        logger.info("Populating files for doi: %s", doi)

        parsed_file["files"] = repo.download_files(parsed_file["files"], prefix=doi)
        logger.info("Files populated: %s", parsed_file["files"])

        return parsed_file

    @task(task_id="jagiellonian-enhance")
    def enhance(enhanced_file):
        return Enhancer()("Jagiellonian", enhanced_file)

    @task(task_id="jagiellonian-enrich")
    def enrich(enhanced_file):
        return Enricher()(enhanced_file)

    @task(task_id="jagiellonian-save-to-s3")
    def save_to_s3(enriched_file, repo=JAGIELLONIAN_REPO):
        upload_json_to_s3(json_record=enriched_file, repo=repo)

    @task()
    def create_or_update(enriched_file):
        create_or_update_article(enriched_file)

    parsed_file = parse()
    parsed_file_with_files = populate_files(parsed_file)
    enhanced_file = enhance(parsed_file_with_files)
    enriched_file = enrich(enhanced_file)
    save_to_s3(enriched_file=enriched_file)
    create_or_update(enriched_file)


dag_for_jagiellonian_files_processing = jagiellonian_process_file()
