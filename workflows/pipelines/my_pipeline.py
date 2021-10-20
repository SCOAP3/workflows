from dagster import pipeline, PresetDefinition, execute_pipeline, ModeDefinition
import os

from workflows.utils.paths import get_ftp_resources_yaml_path
from workflows.resources.ftp_resources import ftp_resource
from workflows.resources.aws_resources import aws_resource
from workflows.resources.download_a_file_from_ftp_solid_config_resources import download_a_file_from_ftp_solid_config_resource
from workflows.collect_save_and_upload_data.solids.connect_to_ftp_server import connect_to_ftp_server
from workflows.collect_save_and_upload_data.solids.collect_files_to_download import collect_files_to_download
from workflows.collect_save_and_upload_data.solids.uploading_files_to_ftp import uploading_files_to_ftp
from workflows.collect_save_and_upload_data.solids.dowloanda_file_from_ftp import download_a_file_from_ftp
from workflows.collect_save_and_upload_data.solids.uploading_files_to_s3 import uploading_files_to_s3
from workflows.collect_save_and_upload_data.solids.unzip import unzip
from workflows.collect_save_and_upload_data.solids.download_file_from_s3 import download_file_from_s3
from workflows.collect_save_and_upload_data.solids.crawler_parser import crawler_parser
from workflows.clean_local_ftp_s3_dirs.combined_cleaning import clean_everything

path_of_ftp_resources_yaml = get_ftp_resources_yaml_path('ftp_resources.yaml')
path_of_ftp_resources_dev_yaml = get_ftp_resources_yaml_path('ftp_resources_dev.yaml')
path_of_aws_resources_yaml = get_ftp_resources_yaml_path('aws_resources_dev.yaml')
path_of_aws_resources_dev_yaml = get_ftp_resources_yaml_path('aws_resources_prod.yaml')
download_a_file_from_ftp_solid_yaml = get_ftp_resources_yaml_path('download_a_file_from_ftp_solid_config_resources.yaml')


@pipeline(
    mode_defs=[
        ModeDefinition(
            name="prod",
            resource_defs={"ftp": ftp_resource, "aws": aws_resource,
                           "download_a_file_from_ftp": download_a_file_from_ftp_solid_config_resource }
        ),
        ModeDefinition(
            name="dev",
            resource_defs={"ftp": ftp_resource, "aws": aws_resource,
                           "download_a_file_from_ftp": download_a_file_from_ftp_solid_config_resource },
        )
    ],
    preset_defs=[
        PresetDefinition.from_files(
            "prod",
            config_files=[
                path_of_ftp_resources_yaml,
                path_of_aws_resources_yaml,
                download_a_file_from_ftp_solid_yaml
            ],
            mode="prod",
        ),
        PresetDefinition.from_files(
            "dev",
            config_files=[
                path_of_ftp_resources_dev_yaml,
                path_of_aws_resources_dev_yaml,
                download_a_file_from_ftp_solid_yaml
            ],
            mode="dev",
        ),
    ],

)

def my_pipeline():
    # clean_everything()
    ftp = connect_to_ftp_server()
    # for testing reasons
    start = uploading_files_to_ftp(ftp)
    collected_files = collect_files_to_download(ftp, start)
    # --- from here we have to follow all files
    downloaded_files = download_a_file_from_ftp(ftp, collected_files)
    paths_for_unzipped_files = unzip(downloaded_files)
    s3_keys = uploading_files_to_s3(paths_for_unzipped_files)
    downloaded_files_with_s3_keys = s3_keys.map(download_file_from_s3)
    file_names = downloaded_files_with_s3_keys.map(crawler_parser)


if __name__ == "__main__":
    # start_presets_main
    result = execute_pipeline(my_pipeline, solid_selection=["ftp"], preset="prod")

    # solids can be run partly, the line below shows how to run composite_solid and it's ancestors.
    # Note: solids has to be used in pipeline directly. For example, if we will put just collect_files_to_download
    # we will get an error: No qualified solids to execute found for solid_selection=['*collect_files_to_download']
    assert result.success
