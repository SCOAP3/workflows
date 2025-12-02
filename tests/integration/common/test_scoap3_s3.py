import os
from unittest.mock import MagicMock

import pytest
import requests
import vcr
from botocore.exceptions import ClientError
from common.scoap3_s3 import Scoap3Repository

my_vcr = vcr.VCR(
    cassette_library_dir="cassettes",
    record_mode="never",
    match_on=["uri", "method"],
)

TEST_URL = (
    "https://s3.amazonaws.com/downloads.hindawi.com/journals/ahep/2024/3681297.pdf"
)

S3_FILE_URL = "https://scoap3-prod-backend.s3.cern.ch/media/harvested_files/10.1155/2024/3681297/3681297.pdf"

NON_EXISTENT_S3_FILE_URL = "https://scoap3-prod-backend.s3.cern.ch/media/harvested_files/10.1155/2024/3681297/12346789.pdf"


@pytest.fixture
def repo():
    os.environ["SCOAP3_BUCKET_NAME"] = "test-bucket"
    os.environ["SCOAP3_BUCKET_UPLOAD_DIR"] = "test-files"
    os.environ["SCOAP3_REPO_S3_ENABLED"] = "True"

    repo = Scoap3Repository()

    repo.client = MagicMock()

    return repo


@my_vcr.use_cassette("head_request_s3_non_existent_file.yaml")
def test_download_and_upload_to_s3_new_file(repo):
    """Test uploading a file that doesn't exist"""

    with my_vcr.use_cassette("head_request_s3_non_existent_file.yaml"):
        head_response = requests.head(NON_EXISTENT_S3_FILE_URL)
        assert head_response.status_code == 403

    def mock_HEAD_request(**kwargs):
        error_response = {"Error": {"Code": "403", "Message": "Forbidden"}}
        raise ClientError(error_response, "HeadObject")

    repo.client.head_object.side_effect = mock_HEAD_request

    result = repo.download_and_upload_to_s3(TEST_URL, prefix="test-prefix", type="pdf")[
        "path"
    ]

    assert result == "test-bucket/test-files/test-prefix/3681297.pdf"

    # Verify put_object was called (file was uploaded)
    repo.client.put_object.assert_called_once()

    call_args = repo.client.put_object.call_args[1]
    assert call_args["Bucket"] == "test-bucket"
    assert call_args["Key"] == "test-files/test-prefix/3681297.pdf"
    assert call_args["ACL"] == "public-read"
    assert call_args["Metadata"] == {"source_url": TEST_URL}
    assert "Body" in call_args


@my_vcr.use_cassette("download_pdf.yaml")
def test_download_and_upload_to_s3_same_checksum(repo):
    """Test when file already exists with the same checksum."""

    with my_vcr.use_cassette("head_request_s3_file.yaml"):
        head_response = requests.head(S3_FILE_URL)
        etag = head_response.headers.get("ETag", "").strip('"')

    def mock_HEAD_request(**kwargs):
        return {"ETag": f'"{etag}"'}

    repo.client.head_object.side_effect = mock_HEAD_request

    result = repo.download_and_upload_to_s3(TEST_URL, prefix="test-prefix", type="pdf")[
        "path"
    ]

    assert result == "test-bucket/test-files/test-prefix/3681297.pdf"

    # Verify put_object was NOT called(file was not uploaded)
    repo.client.put_object.assert_not_called()


@my_vcr.use_cassette("download_pdf.yaml")
def test_download_and_upload_to_s3_different_checksum(repo):
    """Test when file exists but has a different checksum."""

    with my_vcr.use_cassette("head_request_s3_file.yaml"):
        requests.head(S3_FILE_URL)
        etag = "different-checksum-value"  # Override with different value

    def mock_HEAD_request(**kwargs):
        return {"ETag": f'"{etag}"'}

    repo.client.head_object.side_effect = mock_HEAD_request

    result = repo.download_and_upload_to_s3(TEST_URL, prefix="test-prefix", type="pdf")[
        "path"
    ]

    assert result == "test-bucket/test-files/test-prefix/3681297.pdf"

    # Verify put_object was called (file was uploaded)
    repo.client.put_object.assert_called_once()
