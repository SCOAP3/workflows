from unittest import mock
from unittest.mock import MagicMock

import pytest
from airflow.models import DagBag
from jagiellonian.repository import JagiellonianRepository

DAG_NAME = "jagiellonian_pull_api"


@pytest.fixture
def dag():
    dagbag = DagBag(dag_folder="dags/", include_examples=False)
    assert dagbag.import_errors.get(f"dags/{DAG_NAME}.py") is None
    return dagbag.get_dag(dag_id=DAG_NAME)


@pytest.fixture
def repo():
    r = JagiellonianRepository()
    for obj in r.s3_bucket.objects.all():
        obj.delete()
    r.s3_bucket.put_object(Key="test.json", Body=b"")
    yield r
    for obj in r.s3_bucket.objects.all():
        obj.delete()


def test_dag_loaded(dag):
    assert dag is not None


@mock.patch("airflow.providers.http.hooks.http.HttpHook.run")
def test_fetch_crossref_api(mock_http_run, dag, repo):
    mock_http_response = MagicMock()
    mock_http_response.json.return_value = {
        "message": {"items": [], "total-results": 0}
    }
    mock_http_response.raise_for_status = MagicMock()
    mock_http_run.return_value = mock_http_response

    task = dag.get_task("jagiellonian_fetch_crossref_api")
    function_to_unit_test = task.python_callable

    results = function_to_unit_test(repo=repo)

    assert mock_http_run.called

    called_endpoint = mock_http_run.call_args[1]["data"]["filter"]
    assert "from-created-date:" in called_endpoint

    assert results == []
