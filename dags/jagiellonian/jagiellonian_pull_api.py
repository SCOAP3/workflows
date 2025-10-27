import os
from datetime import timedelta

import pendulum
from airflow import settings
from airflow.api.common import trigger_dag
from airflow.decorators import dag, task
from airflow.models import DagRun
from airflow.providers.amazon.aws.hooks.s3 import S3Hook
from airflow.providers.http.hooks.http import HttpHook
from structlog import get_logger

logger = get_logger()


def get_latest_s3_file():
    s3_bucket = os.getenv("JAGIELLONIAN_BUCKET_NAME", "jagiellonian")
    aws_conn_id = os.getenv("AWS_CONN_ID", "aws_s3_minio")

    s3_hook = S3Hook(aws_conn_id=aws_conn_id)
    objects = s3_hook.list_keys(bucket_name=s3_bucket)
    files = [obj for obj in objects if not obj.endswith("/")]
    if not files:
        return None

    file_timestamps = []
    for file_key in files:
        object_info = s3_hook.get_key(key=file_key, bucket_name=s3_bucket)
        file_timestamps.append((file_key, object_info.last_modified))

    file_timestamps.sort(key=lambda x: x[1], reverse=True)
    latest_timestamp = file_timestamps[0][1].strftime("%Y-%m-%d")
    return latest_timestamp


default_args = {
    "owner": "airflow",
    "depends_on_past": False,
    "email_on_failure": False,
    "email_on_retry": False,
    "retries": 1,
    "retry_delay": timedelta(minutes=5),
}


@dag(
    default_args=default_args,
    description="Transfer Crossref journal data to S3",
    schedule="30 */2 * * *",
    start_date=pendulum.today("UTC").add(days=-1),
    catchup=False,
)
def jagiellonian_pull_api(from_date=None):
    @task(task_id="jagiellonian_fetch_crossref_api")
    def fetch_crossref_api(from_date_param=None):
        http_conn_id = os.getenv("HTTP_CONN_ID", "crossref_api")
        endpoint_filter = ""

        if from_date_param:
            logger.info(f"Using provided from_date: {from_date_param}")
            endpoint_filter = f"from-created-date:{from_date_param}"
        else:
            latest_s3_file = get_latest_s3_file()
            if latest_s3_file:
                logger.info(f"Using latest S3 file date: {latest_s3_file}")
                endpoint_filter = f"from-created-date:{latest_s3_file}"
            else:
                logger.info(
                    "No S3 files found and no from_date provided, using no date filter"
                )

        all_results = []
        current_offset = 0
        rows_per_page = 1000
        total_results = None
        jagiellonian_issn = "1509-5770"

        while total_results is None or current_offset < total_results:
            endpoint = f"journals/{jagiellonian_issn}/works"
            params = {
                "rows": rows_per_page,
                "offset": current_offset,
            }
            if endpoint_filter != "":
                params["filter"] = endpoint_filter

            http_hook = HttpHook(method="GET", http_conn_id=http_conn_id)
            response = http_hook.run(endpoint, data=params)
            response.raise_for_status()

            data = response.json()
            page_items = data.get("message", {}).get("items", [])
            all_results.extend(page_items)

            if total_results is None:
                total_results = data.get("message", {}).get("total-results", 0)

            current_offset += rows_per_page

        return all_results

    @task(task_id="jagiellonian_filter_arxiv_category")
    def filter_arxiv_category(data):
        filtered_items = []
        for item in data:
            assertions = item.get("assertion", [])
            if any(
                assertion.get("name") == "arxiv_main_category"
                and assertion.get("value", "").startswith("hep-")
                for assertion in assertions
            ):
                filtered_items.append(item)

        return filtered_items

    @task(task_id="jagiellonian_trigger_file_processing")
    def trigger_file_processing(data):
        for article in data:
            trigger_result = trigger_dag.trigger_dag(
                dag_id="jagiellonian_process_file",
                conf={"article": article},
                replace_microseconds=False,
            )

            note = article.get("DOI", "DOI not found")
            run_id = trigger_result.run_id
            session = settings.Session()
            try:
                dag_run = session.query(DagRun).filter(DagRun.run_id == run_id).one()
                dag_run.note = note
                session.commit()
                logger.info(f"Updated note for DAG run {run_id}")
            except Exception as e:
                logger.error(f"Failed to update note for DAG run {run_id}: {e}")
                session.rollback()
            finally:
                session.close()

    data = fetch_crossref_api(from_date)
    filtered_data = filter_arxiv_category(data)
    trigger_file_processing(filtered_data)


jagiellonian_pull_api_dag = jagiellonian_pull_api()
