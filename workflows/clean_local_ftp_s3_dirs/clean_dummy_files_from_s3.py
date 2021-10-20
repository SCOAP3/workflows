from dagster import solid
import boto3


@solid(required_resource_keys={"aws"})
def clean_dummy_files_from_s3(context):
    aws_access_key_id = context.resources.aws["aws_access_key_id"]
    aws_secret_access_key = context.resources.aws["aws_secret_access_key"]
    endpoint_url = context.resources.aws["endpoint_url"]

    s3_resource = boto3.resource(
        's3',
        aws_access_key_id=aws_access_key_id,
        aws_secret_access_key=aws_secret_access_key,
        endpoint_url=endpoint_url
    )

    bucket_name = context.resources.aws["raw_files_bucket"]
    for obj in s3_resource.Bucket(bucket_name).objects.all():
        s3_resource.Object(bucket_name, obj.key).delete()
        context.log.info(f'Deleting {obj.key} from bucket')

