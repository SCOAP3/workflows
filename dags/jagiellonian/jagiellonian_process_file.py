import json
import logging
import os
from datetime import UTC, datetime
from io import BytesIO

import pendulum
from airflow.providers.amazon.aws.transfers.http_to_s3 import HttpToS3Operator
from airflow.sdk import dag, task
from common.enhancer import Enhancer
from common.enricher import Enricher
from common.notification_service import FailedDagNotifier
from common.utils import create_or_update_article
from jagiellonian.parser import JagiellonianParser
from jagiellonian.repository import JagiellonianRepository

logger = logging.getLogger("airflow.task")
JAGIELLONIAN_REPO = JagiellonianRepository()

FILE_EXTENSIONS = {"pdf": ".pdf", "xml": ".xml", "pdfa": ".pdf"}


def update_filename_extension(filename, type):
    extension = FILE_EXTENSIONS.get(type, "")
    if filename.endswith(extension):
        return filename
    elif extension:
        if type == "pdfa":
            extension = ".a-2b.pdf"
        return f"{filename}{extension}"


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
    def populate_files(parsed_file):
        aws_conn_id = os.getenv("AWS_CONN_ID", "aws_s3_minio")
        scoap3_bucket = os.getenv("SCOAP3_BUCKET_NAME", "scoap3")
        upload_dir = os.getenv("SCOAP3_BUCKET_UPLOAD_DIR", "files")

        if "files" not in parsed_file:
            return parsed_file

        doi = parsed_file.get("dois")[0]["value"]
        logger.info("Populating files for doi: %s", doi)
        files = parsed_file.get("files")

        prefix = doi

        downloaded_files = {}

        for type, url in files.items():
            try:
                filename = os.path.basename(url)
                filename = update_filename_extension(filename, type)

                destination_key = f"{upload_dir}/{prefix}/{filename}"

                transfer_to_s3 = HttpToS3Operator(
                    task_id="transfer-to-s3",
                    endpoint=url,
                    s3_bucket=scoap3_bucket,
                    s3_key=destination_key,
                    aws_conn_id=aws_conn_id,
                    replace=True,
                )

                transfer_to_s3.execute(context={})

                downloaded_files[type] = f"{scoap3_bucket}/{destination_key}"
                logger.info("Downloaded file of type: %s from url: %s", type, url)
            except Exception as e:
                logger.error(
                    "Failed to download file. Error: %s. Type: %s. URL: %s",
                    str(e),
                    type,
                    url,
                )

        parsed_file["files"] = downloaded_files
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
        doi = enriched_file["dois"][0]["value"]
        key = f"{doi}_metadata_{(datetime.now(UTC))}.json"

        repo.save(key=key, obj=BytesIO(json.dumps(enriched_file, indent=2).encode()))

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
