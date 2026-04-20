import pytest
from airflow.models import DagBag
from jagiellonian.repository import JagiellonianRepository

DAG_NAME = "jagiellonian_process_file"


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
    yield r
    for obj in r.s3_bucket.objects.all():
        obj.delete()


def test_dag_loaded(dag):
    assert dag is not None


def test_save_to_s3(dag, repo):
    sample_article = {
        "title": "Test Article",
        "authors": ["Author 1", "Author 2"],
        "abstract": "This is a test abstract",
        "dois": [{"value": "10.1234/test.123"}],
        "files": [],
    }

    task = dag.get_task("jagiellonian-save-to-s3")
    function_to_unit_test = task.python_callable

    function_to_unit_test(sample_article, repo=repo)

    objects = list(repo.s3_bucket.objects.all())
    assert len(objects) == 1
    assert "10.1234/test.123" in objects[0].key
