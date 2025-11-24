import os
from io import BytesIO

from common.exceptions import UnknownFileExtension
from common.repository import IRepository
from common.s3_service import S3Service
from common.utils import find_extension
from structlog import get_logger

logger = get_logger()


class ElsevierRepository(IRepository):
    ZIPED_DIR = "raw/"
    EXTRACTED_DIR = "extracted/"

    def __init__(self):
        super().__init__()
        self.bucket = os.getenv("ELSEVIER_BUCKET_NAME", "elsevier")
        self.s3 = S3Service(self.bucket)

    def get_all_raw_filenames(self):
        return [
            f.key.removeprefix("raw/")
            for f in self.s3.objects.filter(Prefix=self.ZIPED_DIR).all()
        ]

    def find_all(self, filenames_to_process=None):
        grouped_files = {}
        filenames = (
            filenames_to_process
            if filenames_to_process
            else self._find_all_extracted_files()
        )
        try:
            for file in filenames:
                last_part = os.path.basename(file)
                filename_without_extension = last_part.split(".")[0]
                if filename_without_extension not in grouped_files:
                    grouped_files[filename_without_extension] = {}
                extension = find_extension(last_part)
                grouped_files[filename_without_extension][extension] = file
        except (IndexError, UnknownFileExtension):
            self.logger.error()
        return list(grouped_files.values())

    def get_by_id(self, id):
        retfile = BytesIO()
        self.s3.download_fileobj(id, retfile)
        retfile.seek(0)
        return retfile

    def save(self, filename, obj, prefix=None):
        logger.info("Saving file.", filename=filename)
        obj.seek(0)
        if not prefix:
            prefix = (
                self.ZIPED_DIR
                if ".tar" in filename or ".zip" in filename
                else self.EXTRACTED_DIR
            )
        self.s3.upload_fileobj(obj, prefix + filename)

    def delete_all(self):
        self.s3.objects.all().delete()

    def is_meta(self, file):
        if ".xml" in file:
            return file

    def _find_all_extracted_files(self):
        return [
            f.key
            for f in self.s3.objects.filter(Prefix=self.EXTRACTED_DIR).all()
            if ".xml" in f.key or ".pdf" in f.key
        ]
