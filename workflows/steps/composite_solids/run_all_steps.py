from dagster import composite_solid, InputDefinition, String

from workflows.steps.solids.delete_older_workflows import delete_older_workflows
from workflows.steps.solids.add_arxiv_category import add_arxiv_category
from workflows.steps.solids.set_schema import set_schema


@composite_solid(input_defs=[InputDefinition(name="file_name", dagster_type=String)])
def run_all_steps(file_name):
    set_schema(add_arxiv_category(delete_older_workflows(file_name)))
    