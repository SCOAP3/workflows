from io import BytesIO
from unittest.mock import patch

import pytest
from springer.repository import SpringerRepository


class S3BucketResultObj:
    def __init__(self, key) -> None:
        self.key = key


S3_RETURNED_VALUES = [
    "extracted/file1.txt",
    "extracted/file1.scoap",
    "extracted/file1.pdf",
    "extracted/file2.txt",
    "extracted/file2.Meta",
    "extracted/file2.pdf",
]
FIND_ALL_EXPECTED_VALUES = [
    {
        "xml": "extracted/file1.scoap",
        "pdf": "extracted/file1.pdf",
    },
    {
        "xml": "extracted/file2.Meta",
        "pdf": "extracted/file2.pdf",
    },
]
FIND_ALL_EXTRACTED_FILES_EXPECTED_VALUES = [
    "extracted/file1.scoap",
    "extracted/file1.pdf",
    "extracted/file2.Meta",
    "extracted/file2.pdf",
]


@pytest.fixture
def boto3_fixture():
    with patch("common.s3_service.boto3", autospec=True) as boto3_mock:
        boto3_mock.resource.return_value.Bucket.return_value.objects.filter.return_value.all.return_value = [
            S3BucketResultObj(file) for file in S3_RETURNED_VALUES
        ]
        yield boto3_mock


def test_find_all(boto3_fixture):
    repo = SpringerRepository()
    assert repo.find_all() == FIND_ALL_EXPECTED_VALUES


def test_find_all_extracted_files(boto3_fixture):
    repo = SpringerRepository()
    assert (
        repo._SpringerRepository__find_all_extracted_files()
        == FIND_ALL_EXTRACTED_FILES_EXPECTED_VALUES
    )


def test_save_zip_file(boto3_fixture):
    upload_mock = boto3_fixture.resource.return_value.Bucket.return_value.upload_fileobj
    file = BytesIO()
    filename = "test.zip"
    repo = SpringerRepository()
    repo.save(filename, file)
    upload_mock.assert_called_with(file, repo.RAW_DIR + filename)


def test_save_file(boto3_fixture):
    upload_mock = boto3_fixture.resource.return_value.Bucket.return_value.upload_fileobj
    file = BytesIO()
    filename = "test.pdf"
    repo = SpringerRepository()
    repo.save(filename, file)
    upload_mock.assert_called_with(file, repo.EXTRACTED_DIR + filename)


def test_file_is_meta():
    repo = SpringerRepository()
    assert repo.is_meta("test.scoap")
    assert repo.is_meta("test.Meta")
    assert not repo.is_meta("test.test")
