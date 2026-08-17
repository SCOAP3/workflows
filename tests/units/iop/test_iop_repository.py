from io import BytesIO
from unittest.mock import patch

import pytest
from iop.repository import IOPRepository


class S3BucketResultObj:
    def __init__(self, key):
        self.key = key


S3_RETURNED_VALUES = [
    "01_content.pdf",
    "01_content.xml",
    "02_content.pdf",
    "02_content.xml",
    "03_some_random_file.img",
    "text_file.txt",
]

FIND_ALL_EXTRACTED_FILES_EXPECTED_VALUES = [
    "01_content.pdf",
    "01_content.xml",
    "02_content.pdf",
    "02_content.xml",
]

FIND_ALL_EXPECTED_VALUES = [
    {"xml": "01_content.xml", "pdf": "01_content.pdf"},
    {"xml": "02_content.xml", "pdf": "02_content.pdf"},
]

expected_file = BytesIO()


@pytest.fixture
def boto3_fixture():
    with patch("common.s3_service.boto3", autospec=True) as boto3_mock:
        boto3_mock.resource.return_value.Bucket.return_value.objects.filter.return_value.all.return_value = [
            S3BucketResultObj(file) for file in S3_RETURNED_VALUES
        ]
        yield boto3_mock


def test_find_all(boto3_fixture):
    repo = IOPRepository()
    assert repo.find_all() == FIND_ALL_EXPECTED_VALUES


def test_find_all_extracted_files(boto3_fixture):
    repo = IOPRepository()
    assert (
        repo._IOPRepository__find_all_extracted_files()
        == FIND_ALL_EXTRACTED_FILES_EXPECTED_VALUES
    )


def test_save_zip_file(boto3_fixture):
    upload_mock = boto3_fixture.resource.return_value.Bucket.return_value.upload_fileobj
    key = "2022-07-30T03_02_01_content.zip"
    repo = IOPRepository()
    repo.save(key, expected_file)
    upload_mock.assert_called_with(expected_file, f"{repo.RAW_DIR}{key}")


def test_save_file(boto3_fixture):
    upload_mock = boto3_fixture.resource.return_value.Bucket.return_value.upload_fileobj
    file = BytesIO()
    filename = "test.pdf"
    repo = IOPRepository()
    repo.save(filename, file)
    upload_mock.assert_called_with(file, f"{repo.EXTRACTED_DIR}{filename}")
