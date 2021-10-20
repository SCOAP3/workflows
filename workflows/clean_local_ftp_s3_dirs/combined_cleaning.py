from dagster import composite_solid

from workflows.clean_local_ftp_s3_dirs.clean_local import clean_local
from workflows.clean_local_ftp_s3_dirs.clean_dummy_files_from_s3 import clean_dummy_files_from_s3
from workflows.clean_local_ftp_s3_dirs.clean_ftp import clean_ftp


@composite_solid
def clean_everything():
    clean_local()
    clean_dummy_files_from_s3()
    clean_ftp()

    return
