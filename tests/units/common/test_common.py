import zipfile
from io import BytesIO
from unittest.mock import Mock, patch

import pytest
from common.pull_ftp import migrate_from_ftp, reprocess_files, trigger_file_processing
from common.repository import IRepository
from common.sftp_service import SFTPService
from structlog import get_logger

SFTP_NOT_ZIP_FILES: list[str] = ["file2.png"]
SFTP_ZIP_FILES: list[str] = [
    "file1.zip",
    "file2.zip",
]
SFTP_LIST_FILES_RETURN_VALUE: list[str] = SFTP_NOT_ZIP_FILES + SFTP_ZIP_FILES

REPO_FIND_ALL_RETURN_VALUE: list[dict] = [
    {"xml": f, "pdf": f} for f in SFTP_LIST_FILES_RETURN_VALUE
]


class TestRepository(IRepository):
    RAW_DIR = "raw/"
    EXTRACTED_DIR = "extracted/"


@pytest.fixture
def zip_fixture():
    with patch("zipfile.ZipFile", autospec=True) as zip_patch:
        mock_ziparchive = Mock()
        mock_ziparchive.return_value.namelist.return_value = SFTP_ZIP_FILES
        mock_ziparchive.return_value.read.return_value = BytesIO().read()
        zip_patch.return_value.__enter__ = mock_ziparchive
        yield zip_patch


@pytest.fixture
def ftp_get_file_fixture():
    with patch.object(SFTPService, attribute="get_file") as patched:
        patched = patched
        mem_zip = BytesIO()
        with zipfile.ZipFile(mem_zip, mode="w", compression=zipfile.ZIP_DEFLATED) as zf:
            zf.writestr("test.data", b"test")
        patched.side_effect = lambda x: mem_zip if ".zip" in x else BytesIO()
        yield patched


@patch.object(
    SFTPService, attribute="list_files", return_value=SFTP_LIST_FILES_RETURN_VALUE
)
@patch.object(IRepository, attribute="is_meta")
@patch.object(IRepository, attribute="get_all_raw_filenames")
@patch.object(IRepository, attribute="save")
def test_migrate_from_ftp(
    repo_save,
    repo_get_all,
    repo_is_meta,
    sftp_list_files,
    ftp_get_file_fixture,
    zip_fixture,
):
    with SFTPService() as sftp:
        repo = TestRepository()
        migrate_from_ftp(
            sftp,
            repo,
            get_logger().bind(class_name="test_logger"),
            **{
                "params": {
                    "force_pull": False,
                    "excluded_directories": [],
                    "filenames_pull": {
                        "enabled": False,
                        "filenames": [],
                        "force_from_ftp": False,
                    },
                },
            },
        )
        assert repo_save.call_count == len(SFTP_ZIP_FILES) + pow(len(SFTP_ZIP_FILES), 2)


@patch.object(SFTPService, attribute="list_files", return_value=SFTP_ZIP_FILES[0:1])
@patch.object(IRepository, attribute="find_all", return_value=None)
@patch.object(IRepository, attribute="is_meta")
@patch.object(IRepository, attribute="get_all_raw_filenames", return_value=[])
@patch.object(IRepository, attribute="save")
def test_migrate_from_ftp_only_one_file(
    repo_save,
    repo_get_all_raw,
    repo_is_meta,
    find_all,
    sftp_list_files,
    ftp_get_file_fixture,
):
    with SFTPService() as sftp:
        repo = TestRepository()
        migrate_from_ftp(
            sftp,
            repo,
            get_logger().bind(class_name="test_logger"),
            **{
                "params": {
                    "force_pull": False,
                    "excluded_directories": [],
                    "filenames_pull": {
                        "enabled": False,
                        "filenames": [],
                        "force_from_ftp": False,
                    },
                }
            },
        )
        assert repo_save.call_count == len(SFTP_ZIP_FILES[0:1]) + pow(
            len(SFTP_ZIP_FILES[0:1]), 2
        )


@patch.object(
    SFTPService, attribute="list_files", return_value=SFTP_LIST_FILES_RETURN_VALUE
)
@patch.object(IRepository, attribute="is_meta")
@patch.object(IRepository, attribute="get_all_raw_filenames")
@patch.object(IRepository, attribute="save")
def test_migrate_from_ftp_only_one_file_but_force_flag(
    repo_save,
    repo_get_all,
    repo_is_meta,
    sftp_list_files,
    ftp_get_file_fixture,
    zip_fixture,
):
    with SFTPService() as sftp:
        repo = TestRepository()
        repo_get_all.return_value = SFTP_ZIP_FILES[0:-1]
        migrate_from_ftp(
            sftp,
            repo,
            get_logger().bind(class_name="test_logger"),
            **{
                "params": {
                    "excluded_directories": [],
                    "force_pull": True,
                    "filenames_pull": {
                        "enabled": False,
                        "filenames": [],
                        "force_from_ftp": False,
                    },
                }
            },
        )
        assert repo_save.call_count == len(SFTP_ZIP_FILES) + pow(len(SFTP_ZIP_FILES), 2)


@patch.object(
    SFTPService, attribute="list_files", return_value=SFTP_LIST_FILES_RETURN_VALUE
)
@patch.object(IRepository, attribute="is_meta")
@patch.object(IRepository, attribute="get_all_raw_filenames")
@patch.object(IRepository, attribute="save")
def test_migrate_from_ftp_specified_file_force_from_ftp(
    repo_save,
    repo_get_all,
    repo_is_meta,
    sftp_list_files,
    ftp_get_file_fixture,
    zip_fixture,
):
    repo_get_all.return_value = SFTP_ZIP_FILES[0:-1]
    with SFTPService() as sftp:
        repo = TestRepository()
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
                        "filenames": ["file1.zip"],
                        "force_from_ftp": True,
                    },
                }
            },
        )
        assert repo_save.call_count == 3


@patch.object(SFTPService, attribute="__init__", return_value=None)
@patch.object(
    SFTPService, attribute="list_files", return_value=SFTP_LIST_FILES_RETURN_VALUE
)
@patch.object(IRepository, attribute="get_by_id")
@patch.object(IRepository, attribute="is_meta")
@patch.object(IRepository, attribute="get_all_raw_filenames")
@patch.object(IRepository, attribute="save")
def test_migrate_from_ftp_specified_file(
    repo_save,
    repo_get_all,
    repo_is_meta,
    repo_find_by_id,
    sftp_list_files,
    ftp_init,
    ftp_get_file_fixture,
    zip_fixture,
):
    repo_get_all.return_value = SFTP_ZIP_FILES[0:-1]
    repo = TestRepository()
    reprocess_files(
        repo,
        get_logger().bind(class_name="test_logger"),
        **{
            "params": {
                "force_pull": False,
                "excluded_directories": [],
                "filenames_pull": {
                    "enabled": True,
                    "filenames": ["file1.zip"],
                    "force_from_ftp": False,
                },
            }
        },
    )
    assert repo_save.call_count == 0
    assert repo_find_by_id.call_count == 1
    assert repo_is_meta.call_count == 2


@patch.object(IRepository, attribute="get_by_id", return_value=BytesIO(b"test content"))
@patch.object(
    IRepository,
    attribute="find_all",
    return_value=[{"xml": f} for f in SFTP_LIST_FILES_RETURN_VALUE],
)
def test_trigger_file_processing(repo_find_all, repo_get_by_id):
    repo = TestRepository()
    confs = trigger_file_processing(
        "test", repo, get_logger().bind(class_name="test_logger")
    )
    assert len(confs) == 3
    assert "file" in confs[0]
    assert "file_name" in confs[0]
    assert confs[0]["file_name"] == SFTP_LIST_FILES_RETURN_VALUE[0]
