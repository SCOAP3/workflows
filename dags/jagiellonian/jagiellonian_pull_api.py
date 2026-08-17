import logging
import os
from datetime import timedelta

import pendulum
from airflow.providers.http.hooks.http import HttpHook
from airflow.providers.standard.operators.trigger_dagrun import TriggerDagRunOperator
from airflow.sdk import dag, task
from common.notification_service import FailedDagNotifier
from jagiellonian.repository import JagiellonianRepository

logger = logging.getLogger("airflow.task")
JAGIELLONIAN_REPO = JagiellonianRepository()


default_args = {
    "owner": "airflow",
    "depends_on_past": False,
    "email_on_failure": False,
    "email_on_retry": False,
    "retries": 1,
    "retry_delay": timedelta(minutes=5),
}


@dag(
    on_failure_callback=FailedDagNotifier(),
    default_args=default_args,
    description="Transfer Crossref journal data to S3",
    schedule="35 */6 * * *",
    tags=["pull", "jagiellonian"],
    start_date=pendulum.today("UTC").add(days=-1),
    catchup=False,
)
def jagiellonian_pull_api(from_date=None):
    @task(task_id="jagiellonian_fetch_crossref_api")
    def fetch_crossref_api(from_date_param=None, repo=JAGIELLONIAN_REPO):
        http_conn_id = os.getenv("HTTP_CONN_ID", "crossref_api")
        endpoint_filter = ""

        if from_date_param:
            logger.info("Using provided from_date: %s", from_date_param)
            endpoint_filter = f"from-created-date:{from_date_param}"
        else:
            latest_s3_file = repo.find_the_last_uploaded_file_date()
            if latest_s3_file:
                logger.info("Using latest S3 file date: %s", latest_s3_file)
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

    @task(task_id="prepare_trigger_conf")
    def prepare_trigger_conf(data):
        return [{"article": article} for article in data]

    data = fetch_crossref_api(from_date)
    filtered_data = filter_arxiv_category(data)
    trigger_confs = prepare_trigger_conf(filtered_data)

    TriggerDagRunOperator.partial(
        task_id="jagiellonian_trigger_file_processing",
        trigger_dag_id="jagiellonian_process_file",
        reset_dag_run=True,
    ).expand(conf=trigger_confs)


jagiellonian_pull_api_dag = jagiellonian_pull_api()
