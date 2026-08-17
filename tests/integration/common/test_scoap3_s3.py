import os
import uuid
from urllib.parse import urlparse

import pytest
from common.scoap3_s3 import Scoap3Repository
from aps.aps_process_file import (
    populate_files_aps
)

# PDF_URL = "http://harvest.aps.org/v2/journals/articles/10.1000/test.pdf"
# XML_URL = "http://harvest.aps.org/v2/journals/articles/10.1000/test.xml"
PDF_URL = "https://harvest.aps.org/v2/journals/articles/10.1103/rg2q-m515"
XML_URL = "https://harvest.aps.org/v2/journals/articles/10.1103/rg2q-m515"
EXPECTED_CONTENT_TYPES = {"pdf": "application/pdf", "xml": "application/xml"}


@pytest.fixture(scope="session")
def vcr_config(vcr_config):
    s3_host = urlparse(os.getenv("S3_ENDPOINT", "http://localhost:9000")).hostname
    return {**vcr_config, "ignore_hosts": [s3_host]}


@pytest.fixture
def prefix():
    return f"test-{uuid.uuid4()}"


@pytest.fixture
def scoap3_repo(monkeypatch, prefix):
    monkeypatch.setenv("SCOAP3_REPO_S3_ENABLED", "true")
    repo = Scoap3Repository()
    yield repo
    repo.s3.objects.filter(Prefix=f"{repo.upload_dir}/{prefix}").delete()


@pytest.mark.vcr
def test_download_files_uploads_pdf_and_xml_with_correct_content_type(
    scoap3_repo, prefix
):
    json = { "dois": [{"value":"10.1103/cwp5-7c96"}]}
    data = populate_files_aps(json)
    uploaded_files = data.get("files", {})

    assert set(uploaded_files) == {"pdf", "xml"}

    pdf_key = uploaded_files["pdf"].removeprefix(f"{scoap3_repo.bucket}/")
    fetched_pdf = scoap3_repo.client.get_object(Bucket=scoap3_repo.bucket, Key=pdf_key)

    assert fetched_pdf["ContentType"] == EXPECTED_CONTENT_TYPES["pdf"]
    xml_key = uploaded_files["xml"].removeprefix(f"{scoap3_repo.bucket}/")
    fetched_xml = scoap3_repo.client.head_object(Bucket=scoap3_repo.bucket, Key=xml_key)

    assert fetched_xml["ContentType"] == EXPECTED_CONTENT_TYPES["xml"]
