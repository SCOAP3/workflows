import logging
import os
from io import BytesIO
from uuid import uuid4

import requests
from common.repository import IRepository
from common.s3_service import S3Service

logger = logging.getLogger("airflow.task")

FILE_EXTENSIONS = {"pdf": ".pdf", "xml": ".xml", "pdfa": ".pdf"}
CONTENT_TYPES = {"pdf": "application/pdf", "pdfa": "application/pdf", "xml": "application/xml"}


def update_filename_extension(filename, type):
    if type == "pdfa":
        return filename.replace(".pdf", "_a.pdf")

    extension = FILE_EXTENSIONS.get(type, "")
    if filename.endswith(extension):
        return filename
    elif extension:
        return f"{filename}{extension}"


def get_content_type(type, response_headers=None):
    content_type = None
    if response_headers:
        content_type = response_headers.get("Content-Type")
    if content_type:
        if "xml" in content_type:
            return "application/xml"
        if "pdf" in content_type:
            return "application/pdf"
    if not content_type or "octet-stream" in content_type:
        content_type = CONTENT_TYPES.get(type, "binary/octet-stream")
    return content_type


class Scoap3Repository(IRepository):
    def __init__(self):
        super().__init__()
        self.bucket = os.getenv("SCOAP3_BUCKET_NAME", "scoap3")
        self.upload_dir = os.getenv("SCOAP3_BUCKET_UPLOAD_DIR", "files")
        self.upload_enabled = os.getenv("SCOAP3_REPO_S3_ENABLED", False)
        self.s3 = S3Service(self.bucket)
        self.client = self.s3.meta.client

    def copy_file(self, source_bucket, source_key, prefix=None, type=None):
        if not self.upload_enabled:
            return ""

        if not prefix:
            prefix = str(uuid4())

        copy_source = {"Bucket": source_bucket, "Key": source_key}
        filename = os.path.basename(source_key)
        filename = update_filename_extension(filename, type)
        destination_key = f"{self.upload_dir}/{prefix}/{filename}"
        content_type = get_content_type(type)

        logger.info("Copying file from %s", copy_source)
        self.client.copy(
            copy_source,
            self.bucket,
            destination_key,
            ExtraArgs={
                "ContentType": content_type,
                "Metadata": {
                    "source_bucket": source_bucket,
                    "source_key": source_key,
                },
                "MetadataDirective": "REPLACE",
                "ACL": "public-read",
            },
        )
        logger.info("Copied file from %s to %s", source_key, destination_key)
        return f"{self.bucket}/{destination_key}"

    def copy_files(self, bucket, files, prefix=None):
        copied_files = {}
        for type, path in files.items():
            try:
                copied_files[type] = self.copy_file(
                    bucket, path, prefix=prefix, type=type
                )
            except Exception as e:
                logger.error(
                    "Failed to copy file. Error: %s Type: %s Path: %s",
                    str(e),
                    type,
                    path,
                )
        return copied_files

    def get_by_id(self, id):
        key = id.removeprefix(f"{self.bucket}/")
        retfile = BytesIO()
        self.s3.download_fileobj(key, retfile)
        retfile.seek(0)
        return retfile

    def download_files(self, files, prefix=None):
        if not prefix:
            prefix = str(uuid4())

        downloaded_files = {}

        for type, url in files.items():
            try:
                downloaded_files[type] = self.download_and_upload_to_s3(
                    url, prefix=prefix, type=type
                )
                logger.info("Downloaded file %s from %s", type, url)
            except Exception as e:
                logger.error(
                    "Failed to download file. Error: %s Type: %s URL: %s",
                    str(e),
                    type,
                    url,
                )
        return downloaded_files

    def download_files_for_aps(self, files, prefix=None):
        if not prefix:
            prefix = str(uuid4())

        downloaded_files = {}

        for type, url in files.items():
            headers = {
                "Accept": CONTENT_TYPES.get(type),
            }
            try:
                downloaded_files[type] = self.download_and_upload_to_s3(
                    url, prefix=prefix, headers=headers, type=type
                )
                logger.info("Downloaded file %s from %s", type, url)
            except Exception as e:
                logger.error(
                    "Failed to download file. Error: %s Type: %s URL: %s",
                    str(e),
                    type,
                    url,
                )
        return downloaded_files

    def download_and_upload_to_s3(self, url, prefix=None, headers=None, type=None):
        if not self.upload_enabled:
            return ""

        if not prefix:
            prefix = str(uuid4())

        filename = os.path.basename(url)
        filename = update_filename_extension(filename, type)
        destination_key = f"{self.upload_dir}/{prefix}/{filename}"

        response = requests.get(url, headers=headers)
        try:
            response.raise_for_status()
        except requests.exceptions.HTTPError as e:
            logger.error("Failed to download file. Error: %s URL: %s", str(e), url)
            return
        content_type = get_content_type(type, response.headers)
        try:
            self.client.put_object(
                Body=response.content,
                Bucket=self.bucket,
                Key=destination_key,
                ContentType=content_type,  
                Metadata={
                    "source_url": url,
                },
                ACL="public-read",
            )
            return f"{self.bucket}/{destination_key}"
        except Exception as e:
            logger.error(
                "Failed to upload file. Error: %s Bucket: %s Key: %s",
                str(e),
                self.bucket,
                destination_key,
            )
