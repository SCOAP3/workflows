from dagster import solid, InputDefinition, String


@solid(input_defs=[InputDefinition(name="file_name", dagster_type=String)])
def delete_older_workflows(context, file_name):
    context.log.info(f'pseudo delete_older_workflows on file {file_name}')
    return file_name
