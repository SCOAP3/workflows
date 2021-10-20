from dagster import execute_pipeline
from workflows.pipelines.rerun_solids_after_download_file_from_s3 import rerun_solids_after_download_file_from_s3


def teset_rerun_solids_after_download_file_from_s3():
    res = execute_pipeline(rerun_solids_after_download_file_from_s3, preset="prod")
    assert res.success
