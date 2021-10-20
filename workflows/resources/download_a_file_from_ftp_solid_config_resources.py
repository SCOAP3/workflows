from dagster import Field, resource


@resource(config_schema={"specific_files_paths": Field(list)})
def download_a_file_from_ftp_solid_config_resource(context):
    return context.resource_config

