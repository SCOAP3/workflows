import hashlib
import os
from uuid import uuid4

import requests
from botocore.exceptions import ClientError
from common.repository import IRepository
from common.s3_service import S3Service
from structlog import get_logger

logger = get_logger()

FILE_EXTENSIONS = {"pdf": ".pdf", "xml": ".xml", "pdfa": ".pdf"}


def update_filename_extension(filename, type):
    if type == "pdfa":
        return filename.replace(".pdf", "_a.pdf")

    extension = FILE_EXTENSIONS.get(type, "")
    if filename.endswith(extension):
        return filename
    elif extension:
        return f"{filename}{extension}"


def get_file_checksum(data):
    """Calculate MD5 checksum of file data"""
    return hashlib.md5(data).hexdigest()


class Scoap3Repository(IRepository):
    def __init__(self):
        super().__init__()
        self.bucket = os.getenv("SCOAP3_BUCKET_NAME", "scoap3")
        self.upload_dir = os.getenv("SCOAP3_BUCKET_UPLOAD_DIR", "files")
        self.upload_enabled = os.getenv("SCOAP3_REPO_S3_ENABLED", False)
        self.s3 = S3Service(self.bucket)
        self.client = self.s3.meta.client

    def file_exists_with_same_checksum(self, bucket, key, data=None):
        """Check if a file exists at the destination and has the same checksum"""
        try:
            if data:
                # Calculate checksum of data
                data_checksum = get_file_checksum(data)

                # Get destination file if it exists
                try:
                    dest_response = self.client.head_object(Bucket=bucket, Key=key)
                    dest_checksum = dest_response.get("ETag", "").strip('"')

                    # Compare checksums
                    return data_checksum == dest_checksum
                except ClientError as e:
                    if e.response["Error"]["Code"] == "404":
                        # File doesn't exist at destination
                        return False
                    raise

            return False
        except Exception as e:
            logger.error("Error checking file existence", error=str(e))
            return False

    def copy_file(self, source_bucket, source_key, prefix=None, type=None):
        if not self.upload_enabled:
            return ""

        if not prefix:
            prefix = str(uuid4())

        copy_source = {"Bucket": source_bucket, "Key": source_key}
        filename = os.path.basename(source_key)
        filename = update_filename_extension(filename, type)
        destination_key = f"{self.upload_dir}/{prefix}/{filename}"

        logger.info("Copying file from", copy_source=copy_source)
        self.client.copy(
            copy_source,
            self.bucket,
            destination_key,
            ExtraArgs={
                "Metadata": {
                    "source_bucket": source_bucket,
                    "source_key": source_key,
                },
                "MetadataDirective": "REPLACE",
                "ACL": "public-read",
            },
        )
        logger.info(
            f"Copied file from {source_bucket}/{source_key} to {self.bucket}/{destination_key}"
        )
        return f"{self.bucket}/{destination_key}"

    def copy_files(self, bucket, files, prefix=None):
        copied_files = {}
        for type, path in files.items():
            try:
                copied_files[type] = self.copy_file(
                    bucket, path, prefix=prefix, type=type
                )
            except Exception as e:
                logger.error("Failed to copy file.", error=str(e), type=type, path=path)
        return copied_files

    def download_files(self, files, prefix=None):
        if not prefix:
            prefix = str(uuid4())

        downloaded_files = {}

        for type, url in files.items():
            try:
                downloaded_files[type] = self.download_and_upload_to_s3(
                    url, prefix=prefix, type=type
                )
                logger.info("Downloaded file", type=type, url=url)
            except Exception as e:
                logger.error(
                    "Failed to download file.", error=str(e), type=type, url=url
                )
        return downloaded_files

    def download_files_for_aps(self, files, prefix=None):
        if not prefix:
            prefix = str(uuid4())

        downloaded_files = {}

        for type, url in files.items():
            headers = {
                "Accept": f"application/{type}",
            }
            try:
                downloaded_files[type] = self.download_and_upload_to_s3(
                    url, prefix=prefix, headers=headers, type=type
                )
                logger.info("Downloaded file", type=type, url=url)
            except Exception as e:
                logger.error(
                    "Failed to download file.", error=str(e), type=type, url=url
                )
        return downloaded_files

    def download_and_upload_to_s3(self, url, prefix=None, headers=None, type=None):
        if not self.upload_enabled:
            return {"path": "", "version_id": ""}

        if not prefix:
            prefix = str(uuid4())

        filename = os.path.basename(url)
        filename = update_filename_extension(filename, type)
        destination_key = f"{self.upload_dir}/{prefix}/{filename}"

        response = requests.get(url, headers=headers)
        try:
            response.raise_for_status()
        except requests.exceptions.HTTPError as e:
            logger.error("Failed to download file", error=str(e), url=url)
            return {"path": "", "version_id": ""}

        if self.file_exists_with_same_checksum(
            self.bucket, destination_key, data=response.content
        ):
            logger.info(
                "File already exists with the same checksum, skipping upload",
                url=url,
                destination=f"{self.bucket}/{destination_key}",
            )
            try:
                # Get the VersionId using head_object
                head_response = self.client.head_object(
                    Bucket=self.bucket, Key=destination_key
                )
                version_id = head_response.get("VersionId", "")
                return {
                    "path": f"{self.bucket}/{destination_key}",
                    "version_id": version_id,
                }
            except Exception as e:
                logger.error(
                    "Failed to get version ID for existing file",
                    error=str(e),
                    bucket=self.bucket,
                    key=destination_key,
                )
                return {"path": f"{self.bucket}/{destination_key}", "version_id": ""}

        try:
            put_response = self.client.put_object(
                Body=response.content,
                Bucket=self.bucket,
                Key=destination_key,
                Metadata={
                    "source_url": url,
                },
                ACL="public-read",
            )
            # Extract VersionId from the response
            version_id = put_response.get("VersionId", "")
            return {
                "path": f"{self.bucket}/{destination_key}",
                "version_id": version_id,
            }
        except Exception as e:
            logger.error(
                "Failed to upload file",
                error=str(e),
                bucket=self.bucket,
                key=destination_key,
            )
            return {"path": "", "version_id": ""}
