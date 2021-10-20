from dagster import execute_pipeline
from workflows.pipelines.my_pipeline import my_pipeline


def test_my_pipeline():
    """
    This is an example test for a Dagster pipeline.

    For hints on how to test your Dagster pipelines, see our documentation tutorial on Testing:
    https://docs.dagster.io/tutorial/testable
    """
    result = execute_pipeline(my_pipeline, preset="prod")

    assert result.success
