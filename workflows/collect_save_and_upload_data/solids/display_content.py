from dagster import solid, InputDefinition, Any


@solid(
    input_defs=[
        InputDefinition(name='collected_files', dagster_type=Any)
        ])
def display_content(context, collected_files):
    context.log.info(f'Collected file for download: {str(collected_files)}')