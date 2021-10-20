from dagster import solid, InputDefinition, String


@solid(input_defs=[InputDefinition(name="file_name", dagster_type=String)])
def add_arxiv_category(context, file_name):
    context.log.info(f'pseudo add_arxiv_category on file {file_name}')
    return file_name
