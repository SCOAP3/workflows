from dagster import Field, String, resource


@resource(config_schema={"ftp_host": Field(String),
                         "ftp_user": Field(String),
                         "ftp_pass": Field(String),
                         "ftp_folder": Field(String)})
def ftp_resource(context):
    return context.resource_config


