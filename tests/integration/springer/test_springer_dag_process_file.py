import base64
import xml.etree.ElementTree as ET
from io import BytesIO
from zipfile import ZipFile

import pytest
from airflow.models import DagBag
from freezegun import freeze_time
from springer.repository import SpringerRepository
from springer.springer_process_file import (
    springer_enhance_file,
    springer_enrich_file,
    springer_parse_file,
    springer_validate_record,
)

DAG_NAME = "springer_process_file"


def extract_zip_entries(zip_filename):
    with ZipFile(zip_filename, "r") as zip_file:
        return {
            file.filename: zip_file.read(file.filename)
            for file in zip_file.filelist
            if not file.is_dir()
        }


def read_first_xml_from_zip(zip_filename):
    entries = extract_zip_entries(zip_filename)
    xml_files = [
        content
        for filename, content in entries.items()
        if ".Meta" in filename or ".scoap" in filename
    ]
    return xml_files[0]


@pytest.fixture
def dag():
    dagbag = DagBag(dag_folder="dags/", include_examples=False)
    assert dagbag.import_errors.get(f"dags/{DAG_NAME}.py") is None
    return dagbag.get_dag(dag_id=DAG_NAME)


@pytest.fixture
def article():
    data_dir = "./data/springer/JHEP/"
    test_file = "ftp_PUB_19-01-29_20-02-10_JHEP.zip"

    article = ET.fromstring(read_first_xml_from_zip(data_dir + test_file))
    return article


@pytest.fixture
def jhep_data_article():
    data_dir = "./data/springer/JHEP/"
    test_file = "ftp_PUB_26-02-19_08-01-28_data.zip"

    article = ET.fromstring(read_first_xml_from_zip(data_dir + test_file))
    return article


@pytest.fixture
def epjc_data_article():
    data_dir = "./data/springer/EPJC/"
    test_file = "ftp_PUB_26-01-26_08-01-27_data.zip"

    article = ET.fromstring(read_first_xml_from_zip(data_dir + test_file))
    return article


@pytest.fixture
def springer_data_files_in_s3():
    repo = SpringerRepository()
    repo.delete_all()
    archives = [
        (
            "./data/springer/EPJC/ftp_PUB_26-01-26_08-01-27_data.zip",
            "EPJC/ftp_PUB_26-01-26_08-01-27_data",
        ),
        (
            "./data/springer/JHEP/ftp_PUB_26-02-19_08-01-28_data.zip",
            "JHEP/ftp_PUB_26-02-19_08-01-28_data",
        ),
    ]

    for zip_path, s3_prefix in archives:
        for inner_path, content in extract_zip_entries(zip_path).items():
            repo.save(f"{s3_prefix}/{inner_path}", BytesIO(content))

    s3_files = {obj.key for obj in repo.s3.objects.all()}
    assert (
        f"{repo.EXTRACTED_DIR}EPJC/ftp_PUB_26-01-26_08-01-27_data/JOU=10052/VOL=2026.86/ISU=1/ART=15241/BodyRef/PDF/10052_2025_Article_15241.pdf"
        in s3_files
    )
    assert (
        f"{repo.EXTRACTED_DIR}JHEP/ftp_PUB_26-02-19_08-01-28_data/JOU=13130/VOL=2026.2026/ISU=2/ART=28203/BodyRef/PDF/13130_2026_Article_28203.pdf"
        in s3_files
    )

    yield
    repo.delete_all()


def test_dag_loaded(dag):
    assert dag is not None
    assert "parse_file" in dag.task_ids
    assert "add_data_availability" in dag.task_ids
    assert "enhance_file" in dag.task_ids
    assert "populate_files" in dag.task_ids
    assert "enrich_file" in dag.task_ids
    assert "save_to_s3" in dag.task_ids
    assert "create_or_update" in dag.task_ids


publisher = "Springer"
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
    assert expected == springer_enhance_file(test_input)


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
        springer_enrich_file(input_article),
    )


@pytest.mark.vcr
def test_dag_validate_file_pass(article):
    article = {
        "dois": [{"value": "10.1007/JHEP01(2019)210"}],
        "arxiv_eprints": [{"value": "1811.06048", "categories": ["hep-th"]}],
        "page_nr": [29],
        "authors": [
            {
                "surname": "Kubo",
                "given_names": "Naotaka",
                "email": "naotaka.kubo@yukawa.kyoto-u.ac.jp",
                "affiliations": [
                    {
                        "value": "Center for Gravitational Physics, Yukawa Institute for Theoretical Physics, Kyoto University, Sakyo-ku, Kyoto, 606-8502, Japan",
                        "organization": "Kyoto University",
                        "country": "Japan",
                    }
                ],
                "full_name": "Kubo, Naotaka",
            },
            {
                "surname": "Moriyama",
                "given_names": "Sanefumi",
                "email": "moriyama@sci.osaka-cu.ac.jp",
                "affiliations": [
                    {
                        "value": "Department of Physics, Graduate School of Science, Osaka City University, Sumiyoshi-ku, Osaka, 558-8585, Japan",
                        "organization": "Osaka City University",
                        "country": "Japan",
                    },
                    {
                        "value": "Nambu Yoichiro Institute of Theoretical and Experimental Physics (NITEP), Sumiyoshi-ku, Osaka, 558-8585, Japan",
                        "organization": "Nambu Yoichiro Institute of Theoretical and Experimental Physics (NITEP)",
                        "country": "Japan",
                    },
                    {
                        "value": "Osaka City University Advanced Mathematical Institute (OCAMI), Sumiyoshi-ku, Osaka, 558-8585, Japan",
                        "organization": "Osaka City University Advanced Mathematical Institute (OCAMI)",
                        "country": "Japan",
                    },
                ],
                "full_name": "Moriyama, Sanefumi",
            },
            {
                "surname": "Nosaka",
                "given_names": "Tomoki",
                "email": "nosaka@yukawa.kyoto-u.ac.jp",
                "affiliations": [
                    {
                        "value": "School of Physics, Korea Institute for Advanced Study, Dongdaemun-gu, Seoul, 02455, South Korea",
                        "organization": "School of Physics, Korea Institute for Advanced Study",
                        "country": "South Korea",
                    }
                ],
                "full_name": "Nosaka, Tomoki",
            },
        ],
        "license": [
            {
                "license": "CC-BY-3.0",
                "url": "https://creativecommons.org/licenses/by/3.0",
            }
        ],
        "collections": [{"primary": "Journal of High Energy Physics"}],
        "publication_info": [
            {
                "journal_title": "Journal of High Energy Physics",
                "journal_volume": "2019",
                "year": 2019,
                "journal_issue": "1",
                "artid": "JHEP012019210",
                "page_start": "1",
                "page_end": "29",
                "material": "article",
            }
        ],
        "abstracts": [
            {
                "value": "It was known that quantum curves and super Chern-Simons matrix models correspond to each other. From the viewpoint of symmetry, the algebraic curve of genus one, called the del Pezzo curve, enjoys symmetry of the exceptional algebra, while the super Chern-Simons matrix model is described by the free energy of topological strings on the del Pezzo background with the symmetry broken. We study the symmetry breaking of the quantum cousin of the algebraic curve and reproduce the results in the super Chern-Simons matrix model.",
                "source": "Springer",
            }
        ],
        "acquisition_source": {
            "source": "Springer",
            "method": "Springer",
            "date": "2022-06-02T10:59:48.860085",
        },
        "copyright": [{"holder": "SISSA, Trieste, Italy", "year": 2019}],
        "imprints": [{"date": "2019-01-28", "publisher": "Springer"}],
        "record_creation_date": "2022-06-02T10:59:48.860085",
        "titles": [
            {
                "title": "Symmetry breaking in quantum curves and super Chern-Simons matrix models",
                "source": "Springer",
            }
        ],
        "$schema": "http://repo.qa.scoap3.org/schemas/hep.json",
    }
    springer_validate_record(article)


def test_dag_validate_file_fails(article):
    article = {}
    with pytest.raises(KeyError):
        springer_validate_record(article)


def test_dag_process_file_no_input_file(article):
    with pytest.raises(Exception, match="There was no 'file' parameter. Exiting run."):
        springer_parse_file()


def test_extract_data_availability_data(
    dag, epjc_data_article, springer_data_files_in_s3
):
    repo = SpringerRepository()
    expected = {
        "statement": "This manuscript has associated data in a data repository. [Authors' comment: The public release of data supporting the findings of this article will follow the CERN Open Data Policy [124]. Inquiries about plots and tables associated with this article can be addressed to atlas.publications@cern.ch.]\nThismanuscripthasassociatedcode/software in a data repository. [Authors' comment: The ATLAS Collaboration's Athena software, including the configuration of the event generators, is open source (https://gitlab.cern.ch/atlas/athena).]",
        "urls": [
            "https://gitlab.cern.ch/atlas/athena).]",
        ],
    }
    result = dag.test(
        run_conf={
            "file": base64.b64encode(ET.tostring(epjc_data_article)).decode(),
            "file_name": f"{repo.EXTRACTED_DIR}EPJC/ftp_PUB_26-01-26_08-01-27_data/JOU=10052/VOL=2026.86/ISU=1/ART=15241/10052_2025_Article_15241.xml.Meta",
            "parse_pdf": True,
        },
        mark_success_pattern="save_to_s3|create_or_update",
    )
    result = result.get_task_instance("enrich_file").xcom_pull()
    assert "data_availability" in result
    assert result["data_availability"] == expected


def test_extract_data_availability_no_data(
    dag, jhep_data_article, springer_data_files_in_s3
):
    repo = SpringerRepository()
    expected = {
        "statement": "This article has no associated data or the data will not be deposited.\nThis article has no associated code or the code will not be deposited.",
    }
    result = dag.test(
        run_conf={
            "file": base64.b64encode(ET.tostring(jhep_data_article)).decode(),
            "file_name": f"{repo.EXTRACTED_DIR}JHEP/ftp_PUB_26-02-19_08-01-28_data/JOU=13130/VOL=2026.2026/ISU=2/ART=28203/13130_2026_Article_28203.xml.scoap",
            "parse_pdf": True,
        },
        mark_success_pattern="save_to_s3|create_or_update",
    )
    result = result.get_task_instance("enrich_file").xcom_pull()
    assert "data_availability" in result
    assert result["data_availability"] == expected


def test_extract_data_availability_disabled_by_default(
    dag, epjc_data_article, springer_data_files_in_s3
):
    repo = SpringerRepository()
    result = dag.test(
        run_conf={
            "file": base64.b64encode(ET.tostring(epjc_data_article)).decode(),
            "file_name": f"{repo.EXTRACTED_DIR}EPJC/ftp_PUB_26-01-26_08-01-27_data/JOU=10052/VOL=2026.86/ISU=1/ART=15241/10052_2025_Article_15241.xml.Meta",
        },
        mark_success_pattern="save_to_s3|create_or_update",
    )
    result = result.get_task_instance("enrich_file").xcom_pull()
    assert "data_availability" not in result
