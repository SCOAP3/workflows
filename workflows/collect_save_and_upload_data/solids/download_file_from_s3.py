import os
from dagster import solid, InputDefinition
import boto3

from workflows.constants import LOCAL_FOLDER_FOR_DOWNLOADED_FILES_FROM_S3
from workflows.utils.create_dir import create_dir


@solid(required_resource_keys={"aws"},
       input_defs=[InputDefinition(name="s3_key", dagster_type=str)])
def download_file_from_s3(context, s3_key):
    """Downloads file from s3 by received s3 key.
    Credentials for AWS are taken from aws_resources"""

    local_dir = os.path.join(os.getcwd(), LOCAL_FOLDER_FOR_DOWNLOADED_FILES_FROM_S3)
    create_dir(context, os.getcwd(), LOCAL_FOLDER_FOR_DOWNLOADED_FILES_FROM_S3)
    context.log.error(s3_key)
    aws_access_key_id = context.resources.aws["aws_access_key_id"]
    aws_secret_access_key = context.resources.aws["aws_secret_access_key"]
    endpoint_url = context.resources.aws["endpoint_url"]

    s3_client = boto3.client(
        's3',
        aws_access_key_id=aws_access_key_id,
        aws_secret_access_key=aws_secret_access_key,
        endpoint_url=endpoint_url
    )
    bucket_name = context.resources.aws["raw_files_bucket"]

    file_name = os.path.basename(s3_key)
    grouping_folder = os.path.basename(os.path.dirname(s3_key))
    target_path = os.path.join(local_dir, grouping_folder, file_name)
    create_dir(context, local_dir, grouping_folder)
    try:
        s3_client.download_file(bucket_name, s3_key, target_path)
        context.log.info(f'OK: File {s3_key} downloaded successfully to {target_path}')
    except Exception as e:
        context.log.error(f'FAIL: File {s3_key} download fail : {e}')
    finally:
        return s3_key
