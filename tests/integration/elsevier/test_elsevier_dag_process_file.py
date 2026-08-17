import tarfile

import pytest
from airflow.models import DagBag
from common.utils import parse_without_names_spaces
from elsevier.elsevier_file_processing import enhance_elsevier, enrich_elsevier
from elsevier.parser import ElsevierParser
from freezegun import freeze_time

DAG_NAME = "elsevier_process_file"


@pytest.fixture
def dag():
    dagbag = DagBag(dag_folder="dags/", include_examples=False)
    assert dagbag.import_errors.get(f"dags/{DAG_NAME}.py") is None
    return dagbag.get_dag(dag_id=DAG_NAME)


@pytest.fixture
def article():
    data_dir = "./data/elsevier/"
    test_file = "CERNQ000000010669A.tar"

    with tarfile.open(data_dir + test_file, "r") as tar:
        xml_members = [m for m in tar.getmembers() if m.name.endswith("main.xml")]
        xml_bytes = tar.extractfile(xml_members[0]).read()

    xml = parse_without_names_spaces(xml_bytes)
    parser = ElsevierParser()
    return parser.parse(xml)


def test_dag_loaded(dag):
    assert dag is not None
    assert "parse" in dag.task_ids
    assert "enhance" in dag.task_ids
    assert "populate_files" in dag.task_ids
    assert "enrich" in dag.task_ids
    assert "save_to_s3" in dag.task_ids
    assert "create_or_update" in dag.task_ids


publisher = "Elsevier"

generic_pseudo_parser_output = {
    "abstract": "this is abstracts",
    "copyright_holder": "copyright_holder",
    "copyright_year": "2020",
    "copyright_statement": "copyright_statement",
    "copyright_material": "copyright_material",
    "date_published": "2022-05-20",
    "title": "title",
    "subtitle": "subtitle",
}

expected_output = {
    "abstracts": [{"value": "this is abstracts", "source": publisher}],
    "acquisition_source": {
        "source": publisher,
        "method": publisher,
        "date": "2022-05-20T00:00:00",
    },
    "copyright": [
        {
            "holder": "copyright_holder",
            "year": "2020",
            "statement": "copyright_statement",
            "material": "copyright_material",
        }
    ],
    "imprints": [{"date": "2022-05-20", "publisher": publisher}],
    "record_creation_date": "2022-05-20T00:00:00",
    "titles": [{"title": "title", "subtitle": "subtitle", "source": publisher}],
}

empty_generic_pseudo_parser_output = {
    "abstract": "",
    "copyright_holder": "",
    "copyright_year": "",
    "copyright_statement": "",
    "copyright_material": "",
    "date_published": "",
    "title": "",
    "subtitle": "",
}

expected_output_from_empty_input = {
    "abstracts": [{"value": "", "source": publisher}],
    "acquisition_source": {
        "source": publisher,
        "method": publisher,
        "date": "2022-05-20T00:00:00",
    },
    "copyright": [{"holder": "", "year": "", "statement": "", "material": ""}],
    "imprints": [{"date": "", "publisher": publisher}],
    "record_creation_date": "2022-05-20T00:00:00",
    "titles": [{"title": "", "subtitle": "", "source": publisher}],
}


@pytest.mark.parametrize(
    ("test_input", "expected", "publisher"),
    [
        pytest.param(generic_pseudo_parser_output, expected_output, publisher),
        pytest.param(
            empty_generic_pseudo_parser_output,
            expected_output_from_empty_input,
            publisher,
        ),
    ],
)
@freeze_time("2022-05-20")
def test_dag_enhance_file(test_input, expected, publisher):
    assert expected == enhance_elsevier(test_input)


@pytest.mark.vcr
def test_dag_enrich_file(assertListEqual):
    input_article = {
        "arxiv_eprints": [{"value": "2112.01211"}],
        "curated": "Test Value",
        "citeable": "Test Value",
    }
    assertListEqual(
        {
            "arxiv_eprints": [
                {"value": "2112.01211", "categories": list(set(["hep-th", "hep-ph"]))}
            ],
        },
        enrich_elsevier(input_article),
    )
