from dagster import solid, InputDefinition, String


@solid(input_defs=[InputDefinition(name="file_name", dagster_type=String)])
def set_schema(context, file_name):
    context.log.info(f'pseudo set_schema on file {file_name}')
    return file_name
