from airflow.models import DagBag

from common.pull_ftp import migrate_from_ftp, reprocess_files
from elsevier.repository import ElsevierRepository
from elsevier.sftp_service import ElsevierSFTPService
from pytest import fixture
from structlog import get_logger

DAG_NAME = "elsevier_pull_sftp"


@fixture
def dag():
    dagbag = DagBag(dag_folder="dags/", include_examples=False)
    assert dagbag.import_errors.get(f"dags/{DAG_NAME}.py") is None
    return dagbag.get_dag(dag_id=DAG_NAME)


@fixture
def elsevier_empty_repo():
    repo = ElsevierRepository()
    repo.delete_all()
    yield repo


def test_dag_loaded(dag):
    assert dag is not None
    assert len(dag.tasks) == 2


def test_dag_migrate_from_FTP(elsevier_empty_repo):
    assert len(elsevier_empty_repo.find_all()) == 0
    with ElsevierSFTPService() as ftp:
        migrate_from_ftp(
            ftp,
            elsevier_empty_repo,
            get_logger().bind(class_name="test_logger"),
            publisher="elsevier",
            **{
                "params": {
                    "excluded_directories": [],
                    "force_pull": False,
                    "filenames_pull": {
                        "enabled": False,
                        "filenames": [],
                        "force_from_ftp": False,
                    },
                }
            },
        )
        assert elsevier_empty_repo.get_all_raw_filenames() == [
            "CERNQ000000010011A.tar",
            "CERNQ000000010669A.tar",
            "vtex00403986_a-2b_CLEANED.zip",
        ]


def test_dag_migrate_from_FTP_specific_folder(elsevier_empty_repo):
    assert len(elsevier_empty_repo.find_all()) == 0
    with ElsevierSFTPService() as ftp:
        migrate_from_ftp(
            ftp,
            elsevier_empty_repo,
            get_logger().bind(class_name="test_logger"),
            publisher="elsevier",
            **{
                "params": {
                    "excluded_directories": [],
                    "force_pull": False,
                    "filenames_pull": {
                        "enabled": True,
                        "filenames": ["CERNQ000000010669A.tar"],
                        "force_from_ftp": True,
                    },
                }
            },
        )
        assert elsevier_empty_repo.get_all_raw_filenames() == ["CERNQ000000010669A.tar"]

        files = reprocess_files(
            elsevier_empty_repo,
            get_logger().bind(class_name="test_logger"),
            **{
                "params": {
                    "excluded_directories": [],
                    "force_pull": False,
                    "filenames_pull": {
                        "enabled": True,
                        "filenames": ["CERNQ000000010669A.tar"],
                        "force_from_ftp": False,
                    },
                }
            },
        )
        assert files == ['extracted/CERNQ000000010669A/CERNQ000000010669/dataset.xml',
                         'extracted/CERNQ000000010669A/CERNQ000000010669/S0370269323005105/main.xml',
                         'extracted/CERNQ000000010669A/CERNQ000000010669/S0370269323005075/main.xml',
                         'extracted/CERNQ000000010669A/CERNQ000000010669/S0370269323005099/main.xml',]
        assert elsevier_empty_repo.get_all_raw_filenames() == ["CERNQ000000010669A.tar"]
        assert elsevier_empty_repo.find_all() == [{'pdf': 'extracted/CERNQ000000010669A/CERNQ000000010669/S0370269323005105/main.pdf',
                                                   'xml': 'extracted/CERNQ000000010669A/CERNQ000000010669/S0370269323005105/main.xml'},
                                                  {'xml': 'extracted/CERNQ000000010669A/CERNQ000000010669/dataset.xml'}]
