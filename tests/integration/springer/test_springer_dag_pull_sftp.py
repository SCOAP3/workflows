import pytest
from airflow.models import DagBag
from common.pull_ftp import migrate_from_ftp, reprocess_files, trigger_file_processing
from springer.repository import SpringerRepository
from springer.sftp_service import SpringerSFTPService
from structlog import get_logger

DAG_NAME = "springer_pull_sftp"


@pytest.fixture
def dag():
    dagbag = DagBag(dag_folder="dags/", include_examples=False)
    assert dagbag.import_errors.get(f"dags/{DAG_NAME}.py") is None
    return dagbag.get_dag(dag_id=DAG_NAME)


def test_dag_loaded(dag):
    assert dag is not None
    assert "migrate_from_ftp" in dag.task_ids
    assert "prepare_trigger_conf" in dag.task_ids
    assert "springer_trigger_file_processing" in dag.task_ids


def test_dag_run(dag):
    repo = SpringerRepository()
    repo.delete_all()
    dag.test(
        run_conf={
            "filenames_pull": {
                "enabled": True,
                "filenames": ["JHEP/ftp_PUB_19-01-29_20-02-10_JHEP.zip"],
                "force_from_ftp": True,
            },
            "force_pull": False,
            "excluded_directories": [],
        },
        mark_success_pattern="springer_trigger_file_processing",
    )

    expected_subset = [
        {
            "xml": f"{repo.EXTRACTED_DIR}JHEP/ftp_PUB_19-01-29_20-02-10_JHEP/JOU=13130/VOL=2019.2019/ISU=1/ART=9848/13130_2019_Article_9848.xml.scoap",
            "pdf": f"{repo.EXTRACTED_DIR}JHEP/ftp_PUB_19-01-29_20-02-10_JHEP/JOU=13130/VOL=2019.2019/ISU=1/ART=9848/BodyRef/PDF/13130_2019_Article_9848.pdf",
        },
    ]
    found_files = repo.find_all()
    for expected in expected_subset:
        assert expected in found_files

    repo.delete_all()


@pytest.mark.skip
def test_dag_trigger_file_processing():
    repo = SpringerRepository()
    assert [x["xml"] for x in repo.find_all()] == trigger_file_processing(
        "springer", repo, get_logger().bind(class_name="test_logger")
    )


@pytest.mark.skip
def test_force_pull_from_sftp():
    with SpringerSFTPService() as sftp:
        repo = SpringerRepository()
        repo.delete_all()
        assert len(repo.find_all()) == 0
        migrate_from_ftp(
            sftp,
            repo,
            get_logger().bind(class_name="test_logger"),
            **{
                "params": {
                    "force_pull": False,
                    "excluded_directories": [],
                    "filenames_pull": {
                        "enabled": True,
                        "filenames": [
                            "JHEP/ftp_PUB_19-01-29_20-02-10_JHEP.zip",
                            "EPJC/ftp_PUB_19-02-06_16-01-13_EPJC_stripped.zip",
                        ],
                        "force_from_ftp": True,
                    },
                }
            },
        )
        expected_files = [
            {
                "pdf": f"{repo.EXTRACTED_DIR}EPJC/ftp_PUB_19-01-29_20-02-10_EPJC/JOU=10052/VOL=2019.79/ISU=1/ART=6572/BodyRef/PDF/10052_2019_Article_6572.pdf",
                "xml": f"{repo.EXTRACTED_DIR}EPJC/ftp_PUB_19-01-29_20-02-10_EPJC/JOU=10052/VOL=2019.79/ISU=1/ART=6572/10052_2019_Article_6572.xml.Meta",
            },
            {
                "pdf": f"{repo.EXTRACTED_DIR}EPJC/ftp_PUB_19-02-06_16-01-13_EPJC_stripped/JOU=10052/VOL=2019.79/ISU=2/ART=6540/BodyRef/PDF/10052_2019_Article_6540.pdf",
                "xml": f"{repo.EXTRACTED_DIR}EPJC/ftp_PUB_19-02-06_16-01-13_EPJC_stripped/JOU=10052/VOL=2019.79/ISU=2/ART=6540/10052_2019_Article_6540.xml.Meta",
            },
            {
                "pdf": f"{repo.EXTRACTED_DIR}JHEP/ftp_PUB_19-01-29_20-02-10_JHEP/JOU=13130/VOL=2019.2019/ISU=1/ART=9848/BodyRef/PDF/13130_2019_Article_9848.pdf",
                "xml": f"{repo.EXTRACTED_DIR}JHEP/ftp_PUB_19-01-29_20-02-10_JHEP/JOU=13130/VOL=2019.2019/ISU=1/ART=9848/13130_2019_Article_9848.xml.scoap",
            },
        ]
        assert repo.find_all() == expected_files
        repo.delete_all()


@pytest.mark.skip
def test_force_pull_from_sftp_with_excluded_folder():
    with SpringerSFTPService() as sftp:
        repo = SpringerRepository()
        repo.delete_all()
        assert len(repo.find_all()) == 0
        migrate_from_ftp(
            sftp,
            repo,
            get_logger().bind(class_name="test_logger"),
            **{
                "params": {
                    "force_pull": True,
                    "excluded_directories": ["EPJC"],
                    "filenames_pull": {
                        "enabled": False,
                        "filenames": [],
                        "force_from_ftp": False,
                    },
                }
            },
        )
        expected_files = [
            {
                "xml": f"{repo.EXTRACTED_DIR}JHEP/ftp_PUB_19-01-29_20-02-10_JHEP/JOU=13130/VOL=2019.2019/ISU=1/ART=9848/13130_2019_Article_9848.xml.scoap",
                "pdf": f"{repo.EXTRACTED_DIR}JHEP/ftp_PUB_19-01-29_20-02-10_JHEP/JOU=13130/VOL=2019.2019/ISU=1/ART=9848/BodyRef/PDF/13130_2019_Article_9848.pdf",
            }
        ]
        assert repo.find_all() == expected_files
        repo.delete_all()


@pytest.mark.skip
def test_pull_from_sftp_and_reprocess():
    with SpringerSFTPService() as sftp:
        repo = SpringerRepository()
        repo.delete_all()
        assert len(repo.find_all()) == 0
        migrate_from_ftp(
            sftp,
            repo,
            get_logger().bind(class_name="test_logger"),
            **{
                "params": {
                    "force_pull": False,
                    "excluded_directories": [],
                    "filenames_pull": {
                        "enabled": True,
                        "filenames": ["JHEP/ftp_PUB_19-01-29_20-02-10_JHEP.zip"],
                        "force_from_ftp": True,
                    },
                }
            },
        )
        excepted_files = [
            {
                "pdf": f"{repo.EXTRACTED_DIR}EPJC/ftp_PUB_19-01-29_20-02-10_EPJC/JOU=10052/VOL=2019.79/ISU=1/ART=6572/BodyRef/PDF/10052_2019_Article_6572.pdf",
                "xml": f"{repo.EXTRACTED_DIR}EPJC/ftp_PUB_19-01-29_20-02-10_EPJC/JOU=10052/VOL=2019.79/ISU=1/ART=6572/10052_2019_Article_6572.xml.Meta",
            },
            {
                "pdf": f"{repo.EXTRACTED_DIR}EPJC/ftp_PUB_19-02-06_16-01-13_EPJC_stripped/JOU=10052/VOL=2019.79/ISU=2/ART=6540/BodyRef/PDF/10052_2019_Article_6540.pdf",
                "xml": f"{repo.EXTRACTED_DIR}EPJC/ftp_PUB_19-02-06_16-01-13_EPJC_stripped/JOU=10052/VOL=2019.79/ISU=2/ART=6540/10052_2019_Article_6540.xml.Meta",
            },
            {
                "pdf": f"{repo.EXTRACTED_DIR}JHEP/ftp_PUB_19-01-29_20-02-10_JHEP/JOU=13130/VOL=2019.2019/ISU=1/ART=9848/BodyRef/PDF/13130_2019_Article_9848.pdf",
                "xml": f"{repo.EXTRACTED_DIR}JHEP/ftp_PUB_19-01-29_20-02-10_JHEP/JOU=13130/VOL=2019.2019/ISU=1/ART=9848/13130_2019_Article_9848.xml.scoap",
            },
        ]
        assert repo.find_all() == excepted_files

        reprocess_files(
            repo,
            get_logger().bind(class_name="test_logger"),
            **{
                "params": {
                    "force_pull": False,
                    "excluded_directories": [],
                    "filenames_pull": {
                        "enabled": True,
                        "filenames": ["JHEP/ftp_PUB_19-01-29_20-02-10_JHEP.zip"],
                        "force_from_ftp": False,
                    },
                }
            },
        )
        excepted_files = [
            {
                "pdf": f"{repo.EXTRACTED_DIR}EPJC/ftp_PUB_19-01-29_20-02-10_EPJC/JOU=10052/VOL=2019.79/ISU=1/ART=6572/BodyRef/PDF/10052_2019_Article_6572.pdf",
                "xml": f"{repo.EXTRACTED_DIR}EPJC/ftp_PUB_19-01-29_20-02-10_EPJC/JOU=10052/VOL=2019.79/ISU=1/ART=6572/10052_2019_Article_6572.xml.Meta",
            },
            {
                "pdf": f"{repo.EXTRACTED_DIR}EPJC/ftp_PUB_19-02-06_16-01-13_EPJC_stripped/JOU=10052/VOL=2019.79/ISU=2/ART=6540/BodyRef/PDF/10052_2019_Article_6540.pdf",
                "xml": f"{repo.EXTRACTED_DIR}EPJC/ftp_PUB_19-02-06_16-01-13_EPJC_stripped/JOU=10052/VOL=2019.79/ISU=2/ART=6540/10052_2019_Article_6540.xml.Meta",
            },
            {
                "pdf": f"{repo.EXTRACTED_DIR}JHEP/ftp_PUB_19-01-29_20-02-10_JHEP/JOU=13130/VOL=2019.2019/ISU=1/ART=9848/BodyRef/PDF/13130_2019_Article_9848.pdf",
                "xml": f"{repo.EXTRACTED_DIR}JHEP/ftp_PUB_19-01-29_20-02-10_JHEP/JOU=13130/VOL=2019.2019/ISU=1/ART=9848/13130_2019_Article_9848.xml.scoap",
            },
        ]
        assert repo.find_all() == excepted_files
        repo.delete_all()
