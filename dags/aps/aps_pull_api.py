import json
import logging
import os

import pendulum
from airflow.providers.standard.operators.trigger_dagrun import TriggerDagRunOperator
from airflow.sdk import dag, task
from aps.aps_api_client import APSApiClient
from aps.aps_params import APSParams
from aps.repository import APSRepository
from aps.utils import save_file_in_s3, split_json
from common.notification_service import FailedDagNotifier
from common.utils import set_harvesting_interval

APS_REPO = APSRepository()
logger = logging.getLogger("airflow.task")


@dag(
    on_failure_callback=FailedDagNotifier(),
    start_date=pendulum.today("UTC").add(days=-1),
    schedule="0 */6 * * *",
    tags=["pull", "aps"],
    params={"from_date": None, "until_date": None, "per_page": None, "doi": None},
)
def aps_pull_api():
    @task()
    def set_fetching_intervals(repo=APS_REPO, **kwargs):
        return set_harvesting_interval(repo=repo, **kwargs)

    @task()
    def save_json_in_s3(dates: dict, repo=APS_REPO, **kwargs):
        doi = (kwargs.get("params") or {}).get("doi")
        rest_api = APSApiClient(
            base_url=os.getenv("APS_API_BASE_URL", "http://harvest.aps.org")
        )
        if doi:
            articles_metadata = rest_api.get_articles_metadata(doi=doi)
        else:
            parameters = APSParams(
                from_date=dates["from_date"],
                until_date=dates["until_date"],
                per_page=kwargs.get("per_page"),
            ).get_params()
            articles_metadata = rest_api.get_articles_metadata(parameters)
        if articles_metadata is not None:
            return save_file_in_s3(
                data=json.dumps(articles_metadata).encode(), repo=repo
            )
        return None

    @task()
    def prepare_trigger_conf(key, repo=APS_REPO):
        if key is None:
            logger.warning("No new files were downloaded to s3")
            return []
        ids_and_articles = split_json(repo, key)
        return [{"article": json.dumps(item["article"])} for item in ids_and_articles]

    intervals = set_fetching_intervals()
    key = save_json_in_s3(intervals)
    trigger_confs = prepare_trigger_conf(key)

    TriggerDagRunOperator.partial(
        task_id="aps_trigger_file_processing",
        trigger_dag_id="aps_process_file",
        reset_dag_run=True,
    ).expand(conf=trigger_confs)


APS_download_files_dag = aps_pull_api()
