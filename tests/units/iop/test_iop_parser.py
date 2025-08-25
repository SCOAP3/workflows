import xml.etree.ElementTree as ET

from common.cleanup import replace_cdata_format
from common.constants import ARXIV_EXTRACTION_PATTERN
from common.enhancer import Enhancer
from common.exceptions import UnknownLicense
from common.parsing.xml_extractors import RequiredFieldNotFoundExtractionError
from common.utils import parse_element_text, parse_to_ET_element
from iop.iop_process_file import convert_xml_to_et_tree
from iop.parser import IOPParser
from pytest import fixture, mark, param, raises


@fixture
def parser():
    return IOPParser()


def test_doi(shared_datadir, parser):
    content = (shared_datadir / "just_required_fields.xml").read_text()
    article = parse_to_ET_element(content)
    parsed_article = parser._publisher_specific_parsing(article)
    assert parsed_article["dois"] == ["10.1088/1674-1137/ac66cc"]


def test_no_doi(shared_datadir, parser):
    content = (shared_datadir / "no_data.xml").read_text()
    article = parse_to_ET_element(content)
    with raises(RequiredFieldNotFoundExtractionError):
        parser._publisher_specific_parsing(article)


def test_no_doi_in_text(shared_datadir, parser):
    content = (shared_datadir / "just_fields_no_text_data.xml").read_text()
    article = parse_to_ET_element(content)
    with raises(RequiredFieldNotFoundExtractionError):
        parser._publisher_specific_parsing(article)


def test_journal_doctype(shared_datadir, parser):
    content = (shared_datadir / "just_required_fields.xml").read_text()
    article = parse_to_ET_element(content)
    parsed_article = parser._publisher_specific_parsing(article)
    assert parsed_article["journal_doctype"] == "article"


def test_no_journal_doctype(shared_datadir, parser):
    content = (shared_datadir / "without_journal_doc_type.xml").read_text()
    article = parse_to_ET_element(content)
    parsed_article = parser._publisher_specific_parsing(article)
    assert "journal_doctype" not in parsed_article


def test_no_journal_doctype_in_attribute(shared_datadir, parser):
    content = (
        shared_datadir / "without_journal_doc_type_attribute_value.xml"
    ).read_text()
    article = parse_to_ET_element(content)
    parsed_article = parser._publisher_specific_parsing(article)
    assert "journal_doctype" not in parsed_article


def test_journal_doctype_with_wrong_value(shared_datadir, parser):
    content = (shared_datadir / "all_fields_wrong_values.xml").read_text()
    article = parse_to_ET_element(content)
    parsed_article = parser._publisher_specific_parsing(article)
    assert "journal_doctype" not in parsed_article


def test_related_article_doi(shared_datadir, parser):
    content = (shared_datadir / "related_article_dois.xml").read_text()
    article = parse_to_ET_element(content)
    parsed_article = parser._publisher_specific_parsing(article)
    assert parsed_article["related_article_doi"] == ["10.0000/0000-0000/aa00aa"]


def test_no_related_article_dois(shared_datadir, parser):
    content = (shared_datadir / "related_article_dois_no_path.xml").read_text()
    article = parse_to_ET_element(content)
    parsed_article = parser._publisher_specific_parsing(article)
    assert "related_article_doi" not in parsed_article


def test_related_article_dois_no_value(shared_datadir, parser):
    content = (shared_datadir / "related_article_dois_no_value.xml").read_text()
    article = parse_to_ET_element(content)
    parsed_article = parser._publisher_specific_parsing(article)
    assert "related_article_doi" not in parsed_article


def test_arxiv_eprints(shared_datadir, parser):
    content = (shared_datadir / "arxiv_eprints.xml").read_text()
    article = parse_to_ET_element(content)
    parsed_article = parser._publisher_specific_parsing(article)
    assert parsed_article["arxiv_eprints"] == [{"value": "2108.04010"}]


def test_no_arxiv_eprints(shared_datadir, parser):
    content = (shared_datadir / "no_arxiv_eprints.xml").read_text()
    article = parse_to_ET_element(content)
    parsed_article = parser._publisher_specific_parsing(article)
    assert "arxiv_eprints" not in parsed_article


def test_no_arxiv_eprints_value(shared_datadir, parser):
    content = (shared_datadir / "no_arxiv_eprints_value.xml").read_text()
    article = parse_to_ET_element(content)
    parsed_article = parser._publisher_specific_parsing(article)
    assert "arxiv_eprints" not in parsed_article


def test_arxiv_eprints_value_with_version(shared_datadir, parser):
    content = (shared_datadir / "arxiv_eprints_with_version.xml").read_text()
    article = parse_to_ET_element(content)
    parsed_article = parser._publisher_specific_parsing(article)
    assert parsed_article["arxiv_eprints"] == [{"value": "2108.04010"}]


@fixture
@mark.parametrize(
    "input, expected",
    [
        param("1111.111123", "1111.111123", id="test_arxiv_value_with_digits"),
        param(
            "1111.111wtwtwvqv1",
            "1111.111wtwtwvq",
            id="test_arxiv_value_with_digits_and_letters_and_version",
        ),
        param(
            "1111.111123v1",
            "1111.111123",
            id="test_arxiv_value_with_digits_and_version",
        ),
    ],
)
def test_arxiv_extraction_pattern(expected, input):
    assert ARXIV_EXTRACTION_PATTERN.sub("", input) == expected


def test_page_nr(shared_datadir, parser):
    content = (shared_datadir / "page_nr.xml").read_text()
    article = parse_to_ET_element(content)
    parsed_article = parser._publisher_specific_parsing(article)
    assert parsed_article["page_nr"] == [9]


def test_no_page_nr_path(shared_datadir, parser):
    content = (shared_datadir / "no_page_nr_path.xml").read_text()
    article = parse_to_ET_element(content)
    parsed_article = parser._publisher_specific_parsing(article)
    assert "page_nr" not in parsed_article


def test_page_nr_wrong_value(shared_datadir, parser):
    content = (shared_datadir / "page_nr_wrong_value.xml").read_text()
    article = parse_to_ET_element(content)
    parsed_article = parser._publisher_specific_parsing(article)
    assert "page_nr" not in parsed_article


def test_page_nr_no_value(shared_datadir, parser):
    content = (shared_datadir / "page_nr_no_value.xml").read_text()
    article = parse_to_ET_element(content)
    parsed_article = parser._publisher_specific_parsing(article)
    assert "page_nr" not in parsed_article


def test_date_published(shared_datadir, parser):
    content = (shared_datadir / "all_fields.xml").read_text()
    article = ET.fromstring(content)
    parsed_article = parser._publisher_specific_parsing(article)
    assert parsed_article["date_published"] == "2022-08-01"
    assert parsed_article["journal_year"] == 2022


def test_authors_no_surname(shared_datadir, parser):
    content = (shared_datadir / "no_author_surname.xml").read_text()
    article = ET.fromstring(content)
    parsed_article = parser._publisher_specific_parsing(article)
    parsed_article = parser._generic_parsing(parsed_article)

    no_surname = []
    for pa in parsed_article["authors"]:
        if not pa.get("surname"):
            no_surname.append(pa)
    assert len(no_surname) > 0


def test_convert_string():
    fail_string = '<p>As mentioned before, we say that an operator is conserved if its expectation value is independent of time. This means that an equal-time operator <italic toggle="yes">A</italic> is conserved if and only if it satisfies <italic toggle="yes"/>d<italic toggle="yes">A</italic>=0. Thus, we have a tool allowing us to identify the conserved operators without resorting to Noether\'s theorem.</p>'

    parsed_article = convert_xml_to_et_tree(fail_string)
    assert parsed_article


def test_authors_faulty_xml(shared_datadir, parser):
    content = (shared_datadir / "faulty_xml.xml").read_text()

    article = convert_xml_to_et_tree(content)
    parsed_article = parser._publisher_specific_parsing(article)
    parsed_article = parser._generic_parsing(parsed_article)

    assert parsed_article


def test_authors(shared_datadir, parser):
    content = (shared_datadir / "all_fields.xml").read_text()
    article = ET.fromstring(content)
    parsed_article = parser._publisher_specific_parsing(article)
    assert parsed_article["authors"] == [
        {
            "surname": "Zhao",
            "given_names": "Lin",
            "affiliations": [
                {
                    "country": "China",
                    "organization": "Department of Engineering Physics, Tsinghua University, China",
                },
                {
                    "country": "China",
                    "organization": "Center for High Energy Physics, Tsinghua University, China",
                },
            ],
        },
        {
            "surname": "Luo",
            "given_names": "Wentai",
            "affiliations": [
                {
                    "country": "China",
                    "organization": "School of Physical Sciences, University of Chinese Academy of Sciences, China",
                }
            ],
        },
        {
            "surname": "Bathe-Peters",
            "given_names": "Lars",
            "affiliations": [
                {
                    "country": "China",
                    "organization": "Department of Engineering Physics, Tsinghua University, China",
                },
                {
                    "country": "Germany",
                    "organization": "Institut für Physik, Technische Universität Berlin, Germany",
                },
            ],
        },
        {
            "surname": "Chen",
            "given_names": "Shaomin",
            "affiliations": [
                {
                    "country": "China",
                    "organization": "Department of Engineering Physics, Tsinghua University, China",
                },
                {
                    "country": "China",
                    "organization": "Center for High Energy Physics, Tsinghua University, China",
                },
                {
                    "country": "China",
                    "organization": "Key Laboratory of Particle & Radiation Imaging (Tsinghua University), China",
                },
            ],
        },
        {
            "surname": "Chouaki",
            "given_names": "Mourad",
            "affiliations": [
                {
                    "country": "China",
                    "organization": "Department of Engineering Physics, Tsinghua University, China",
                },
                {
                    "country": "Switzerland",
                    "organization": "École Polytechnique Fédérale de Lausanne, Switzerland",
                },
            ],
        },
        {
            "surname": "Dou",
            "given_names": "Wei",
            "affiliations": [
                {
                    "country": "China",
                    "organization": "Department of Engineering Physics, Tsinghua University, China",
                },
                {
                    "country": "China",
                    "organization": "Center for High Energy Physics, Tsinghua University, China",
                },
            ],
        },
        {
            "surname": "Guo",
            "given_names": "Lei",
            "affiliations": [
                {
                    "country": "China",
                    "organization": "Department of Engineering Physics, Tsinghua University, China",
                },
                {
                    "country": "China",
                    "organization": "Center for High Energy Physics, Tsinghua University, China",
                },
            ],
        },
        {
            "surname": "Guo",
            "given_names": "Ziyi",
            "affiliations": [
                {
                    "country": "China",
                    "organization": "Department of Engineering Physics, Tsinghua University, China",
                },
                {
                    "country": "China",
                    "organization": "Center for High Energy Physics, Tsinghua University, China",
                },
            ],
        },
        {
            "surname": "Hussain",
            "given_names": "Ghulam",
            "affiliations": [
                {
                    "country": "China",
                    "organization": "Department of Engineering Physics, Tsinghua University, China",
                },
                {
                    "country": "China",
                    "organization": "Center for High Energy Physics, Tsinghua University, China",
                },
            ],
        },
        {
            "surname": "Li",
            "given_names": "Jinjing",
            "affiliations": [
                {
                    "country": "China",
                    "organization": "Department of Engineering Physics, Tsinghua University, China",
                },
                {
                    "country": "China",
                    "organization": "Center for High Energy Physics, Tsinghua University, China",
                },
            ],
        },
        {
            "surname": "Liang",
            "given_names": "Ye",
            "affiliations": [
                {
                    "country": "China",
                    "organization": "Department of Engineering Physics, Tsinghua University, China",
                },
                {
                    "country": "China",
                    "organization": "Center for High Energy Physics, Tsinghua University, China",
                },
            ],
        },
        {
            "surname": "Liu",
            "given_names": "Qian",
            "affiliations": [
                {
                    "country": "China",
                    "organization": "School of Physical Sciences, University of Chinese Academy of Sciences, China",
                }
            ],
        },
        {
            "surname": "Luo",
            "given_names": "Guang",
            "affiliations": [
                {
                    "country": "China",
                    "organization": "School of Physics, Sun Yat-Sen University, China",
                }
            ],
        },
        {
            "surname": "Qi",
            "given_names": "Ming",
            "affiliations": [
                {
                    "country": "China",
                    "organization": "School of Physics, Nanjing University, China",
                }
            ],
        },
        {
            "surname": "Shao",
            "given_names": "Wenhui",
            "affiliations": [
                {
                    "country": "China",
                    "organization": "Department of Engineering Physics, Tsinghua University, China",
                },
                {
                    "country": "China",
                    "organization": "Center for High Energy Physics, Tsinghua University, China",
                },
            ],
        },
        {
            "surname": "Tang",
            "given_names": "Jian",
            "affiliations": [
                {
                    "country": "China",
                    "organization": "School of Physics, Sun Yat-Sen University, China",
                }
            ],
        },
        {
            "surname": "Wan",
            "given_names": "Linyan",
            "affiliations": [
                {
                    "country": "China",
                    "organization": "Department of Engineering Physics, Tsinghua University, China",
                },
                {
                    "country": "China",
                    "organization": "Center for High Energy Physics, Tsinghua University, China",
                },
            ],
        },
        {
            "surname": "Wang",
            "given_names": "Zhe",
            "affiliations": [
                {
                    "country": "China",
                    "organization": "Department of Engineering Physics, Tsinghua University, China",
                },
                {
                    "country": "China",
                    "organization": "Center for High Energy Physics, Tsinghua University, China",
                },
                {
                    "country": "China",
                    "organization": "Key Laboratory of Particle & Radiation Imaging (Tsinghua University), China",
                },
            ],
        },
        {
            "surname": "Wu",
            "given_names": "Yiyang",
            "affiliations": [
                {
                    "country": "China",
                    "organization": "Department of Engineering Physics, Tsinghua University, China",
                },
                {
                    "country": "China",
                    "organization": "Center for High Energy Physics, Tsinghua University, China",
                },
            ],
        },
        {
            "surname": "Xu",
            "given_names": "Benda",
            "email": "orv@tsinghua.edu.cn",
            "affiliations": [
                {
                    "country": "China",
                    "organization": "Department of Engineering Physics, Tsinghua University, China",
                },
                {
                    "country": "China",
                    "organization": "Center for High Energy Physics, Tsinghua University, China",
                },
                {
                    "country": "China",
                    "organization": "Key Laboratory of Particle & Radiation Imaging (Tsinghua University), China",
                },
            ],
        },
        {
            "surname": "Xu",
            "given_names": "Tong",
            "affiliations": [
                {
                    "country": "China",
                    "organization": "Department of Engineering Physics, Tsinghua University, China",
                },
                {
                    "country": "China",
                    "organization": "Center for High Energy Physics, Tsinghua University, China",
                },
            ],
        },
        {
            "surname": "Xu",
            "given_names": "Weiran",
            "affiliations": [
                {
                    "country": "China",
                    "organization": "Department of Engineering Physics, Tsinghua University, China",
                },
                {
                    "country": "China",
                    "organization": "Center for High Energy Physics, Tsinghua University, China",
                },
            ],
        },
        {
            "surname": "Yang",
            "given_names": "Yuzi",
            "affiliations": [
                {
                    "country": "China",
                    "organization": "Department of Engineering Physics, Tsinghua University, China",
                },
                {
                    "country": "China",
                    "organization": "Center for High Energy Physics, Tsinghua University, China",
                },
            ],
        },
        {
            "surname": "Yeh",
            "given_names": "Minfang",
            "affiliations": [
                {
                    "country": "United States",
                    "organization": "Brookhaven National Laboratory, Upton, United States",
                }
            ],
        },
        {
            "surname": "Zhang",
            "given_names": "Aiqiang",
            "affiliations": [
                {
                    "country": "China",
                    "organization": "Department of Engineering Physics, Tsinghua University, China",
                },
                {
                    "country": "China",
                    "organization": "Center for High Energy Physics, Tsinghua University, China",
                },
            ],
        },
        {
            "surname": "Zhang",
            "given_names": "Bin",
            "affiliations": [
                {
                    "country": "China",
                    "organization": "Department of Engineering Physics, Tsinghua University, China",
                },
                {
                    "country": "China",
                    "organization": "Center for High Energy Physics, Tsinghua University, China",
                },
            ],
        },
    ]


def test_no_authors(shared_datadir, parser):
    content = (shared_datadir / "no_authors.xml").read_text()
    article = ET.fromstring(content)
    with raises(RequiredFieldNotFoundExtractionError):
        parser._publisher_specific_parsing(article)


def test_title(shared_datadir, parser):
    content = (shared_datadir / "title_and_abstract_with_cdata.xml").read_text()
    content = replace_cdata_format(content)

    article = ET.fromstring(content)
    parsed_article = parser._publisher_specific_parsing(article)
    assert (
        parsed_article["title"]
        == r"Analysis of ${{\\boldsymbol b}{\\bf\\rightarrow} {\\boldsymbol c}{\\boldsymbol\\tau}"
        r"\\bar{\\boldsymbol\\nu}_{\\boldsymbol\\tau}}$ anomalies using weak effective Hamiltonian"
        r" with complex couplings and their impact on various physical observables"
    )


def test_abstract(shared_datadir, parser):
    content = (shared_datadir / "abstract.xml").read_text()
    article = convert_xml_to_et_tree(content)
    parsed_article = parser._publisher_specific_parsing(article)
    assert (
        parsed_article["abstract"]
        == r"Solar, terrestrial, and supernova neutrino experiments are subject to muon-induced"
        r" radioactive background. The China Jinping Underground Laboratory (CJPL), with its "
        r"unique advantage of a 2400 m rock coverage and long distance from nuclear power plants,"
        r" is ideal for MeV-scale neutrino experiments. Using a 1-ton prototype detector of the "
        r"Jinping Neutrino Experiment (JNE), we detected 343 high-energy cosmic-ray muons and "
        r"(7.86 $ \pm $ 3.97) muon-induced neutrons from an 820.28-day dataset at the first "
        r"phase of CJPL (CJPL-I). Based on the muon-induced neutrons, we measured the corresponding "
        r"muon-induced neutron yield in a liquid scintillator to be $(3.44 \pm 1.86_{\rm stat.}\pm $"
        r" $ 0.76_{\rm syst.})\times 10^{-4}$ μ $^{−1}$ g $^{−1}$ cm $^{2}$ at an average muon energy"
        r" of 340 GeV. We provided the first study for such neutron background at CJPL. A global fit "
        r"including this measurement shows a power-law coefficient of (0.75 $ \pm $ 0.02) for the "
        r"dependence of the neutron yield at the liquid scintillator on muon energy."
    )


def test_no_abstract(shared_datadir, parser):
    content = (shared_datadir / "no_abstract.xml").read_text()
    article = parse_to_ET_element(content)
    with raises(RequiredFieldNotFoundExtractionError):
        parser._publisher_specific_parsing(article)


def test_no_month_published(shared_datadir, parser):
    content = (shared_datadir / "no_month_published.xml").read_text()
    article = ET.fromstring(content)
    parsed_article = parser._publisher_specific_parsing(article)
    assert parsed_article["journal_year"] == 2022
    assert parsed_article["date_published"] == "2022"


def test_no_day_published(shared_datadir, parser):
    content = (shared_datadir / "no_day_published.xml").read_text()
    article = ET.fromstring(content)
    parsed_article = parser._publisher_specific_parsing(article)
    assert parsed_article["date_published"] == "2022-08"
    assert parsed_article["journal_year"] == 2022


def test_no_year_published(shared_datadir, parser):
    content = (shared_datadir / "no_year_published.xml").read_text()
    article = ET.fromstring(content)
    with raises(RequiredFieldNotFoundExtractionError):
        parser._publisher_specific_parsing(article)


def test_no_authors_institutions(shared_datadir, parser):
    content = (shared_datadir / "no_authors_institutions.xml").read_text()
    article = ET.fromstring(content)
    parsed_article = parser._publisher_specific_parsing(article)
    assert parsed_article["authors"] == [
        {
            "surname": "Zhao",
            "given_names": "Lin",
            "affiliations": [{"country": "China"}, {"country": "China"}],
        }
    ]


def test_no_authors_country(shared_datadir, parser):
    content = (shared_datadir / "no_authors_country.xml").read_text()
    article = ET.fromstring(content)
    parsed_article = parser._publisher_specific_parsing(article)
    assert parsed_article["authors"] == [{"given_names": "Lin", "surname": "Zhao"}]


def test_no_authors_and_institutions_country(shared_datadir, parser):
    content = (shared_datadir / "no_authors_and_institutions_country.xml").read_text()
    article = ET.fromstring(content)
    with raises(RequiredFieldNotFoundExtractionError):
        parser._publisher_specific_parsing(article)


def test_authors_with_missing_fields(shared_datadir, parser):
    content = (shared_datadir / "authors_with_missing_fields.xml").read_text()
    article = ET.fromstring(content)
    parsed_article = parser._publisher_specific_parsing(article)
    assert parsed_article["authors"] == [
        {
            "surname": "Zhao",
            "given_names": "林",  # the author misses given_names, so it's taken from name-style="eastern"
            "affiliations": [
                {
                    "country": "China",
                    "organization": "Department of Engineering Physics, Tsinghua University, China",
                },
                {
                    "country": "China",
                    "organization": "Department of Engineering Physics, Tsinghua University, China",
                },
            ],
        },
        {
            "surname": "Test1",  # the author misses given_names
            "affiliations": [
                {
                    "country": "China",
                    "organization": "Department of Engineering Physics, Tsinghua University, China",
                },
                {
                    "country": "China",
                    "organization": "Department of Engineering Physics, Tsinghua University, China",
                },
            ],
        },
        {
            "affiliations": [  # the author misses given_names and name
                {
                    "country": "China",
                    "organization": "Department of Engineering Physics, Tsinghua University, China",
                },
                {
                    "country": "China",
                    "organization": "Department of Engineering Physics, Tsinghua University, China",
                },
            ]
        },
    ]


def test_copyright(shared_datadir, parser):
    content = (shared_datadir / "just_required_fields.xml").read_text()
    article = ET.fromstring(content)
    parsed_article = parser._publisher_specific_parsing(article)
    assert parsed_article["copyright_year"] == "2022"
    assert (
        parsed_article["copyright_statement"]
        == "© 2022 Chinese Physical Society and the Institute of High Energy Physics of the Chinese Academy of Sciences and the Institute of Modern Physics of the Chinese Academy of Sciences and IOP Publishing Ltd"
    )


def test_copyright_no_year(shared_datadir, parser):
    content = (shared_datadir / "no_copyright_year.xml").read_text()
    article = ET.fromstring(content)
    parsed_article = parser._publisher_specific_parsing(article)
    assert (
        parsed_article["copyright_statement"]
        == "© 2022 Chinese Physical Society and the Institute of High Energy Physics of the Chinese Academy of Sciences and the Institute of Modern Physics of the Chinese Academy of Sciences and IOP Publishing Ltd"
    )


def test_copyright_no_year_value(shared_datadir, parser):
    content = (shared_datadir / "no_copyright_year_value.xml").read_text()
    article = ET.fromstring(content)
    parsed_article = parser._publisher_specific_parsing(article)
    assert (
        parsed_article["copyright_statement"]
        == "© 2022 Chinese Physical Society and the Institute of High Energy Physics of the Chinese Academy of Sciences and the Institute of Modern Physics of the Chinese Academy of Sciences and IOP Publishing Ltd"
    )


def test_copyright_no_statement(shared_datadir, parser):
    content = (shared_datadir / "no_copyright_statement.xml").read_text()
    article = ET.fromstring(content)
    parsed_article = parser._publisher_specific_parsing(article)
    assert parsed_article["copyright_year"] == "2022"


def test_copyright_no_statement_value(shared_datadir, parser):
    content = (shared_datadir / "no_copyright_statement_value.xml").read_text()
    article = ET.fromstring(content)
    parsed_article = parser._publisher_specific_parsing(article)
    assert parsed_article["copyright_year"] == "2022"


def test_publication_info(shared_datadir, parser):
    content = (shared_datadir / "all_fields.xml").read_text()
    article = ET.fromstring(content)
    parsed_article = parser._publisher_specific_parsing(article)
    assert parsed_article["journal_title"] == "Chinese Physics C"
    assert parsed_article["journal_volume"] == "46"
    assert parsed_article["journal_issue"] == "8"
    assert parsed_article["journal_artid"] == "085001"
    assert parsed_article["journal_year"] == 2022


def test_publication_info_just_journal_title_year(shared_datadir, parser):
    content = (shared_datadir / "just_journal_year.xml").read_text()
    article = ET.fromstring(content)
    with raises(RequiredFieldNotFoundExtractionError):
        parser._publisher_specific_parsing(article)


def test_licenses(shared_datadir, parser):
    content = (shared_datadir / "just_required_fields.xml").read_text()
    article = ET.fromstring(content)
    parsed_article = parser._publisher_specific_parsing(article)
    assert parsed_article["license"] == [
        {"license": "CC-BY-3.0", "url": "http://creativecommons.org/licenses/by/3.0/"}
    ]


def test_no_licenses_and_no_statements(shared_datadir, parser):
    content = (shared_datadir / "no_license_and_no_statement_no_url.xml").read_text()
    article = ET.fromstring(content)
    with raises(RequiredFieldNotFoundExtractionError):
        parser._publisher_specific_parsing(article)


def test_no_abstract_value(shared_datadir, parser):
    content = (shared_datadir / "no_abstract_value.xml").read_text()
    article = parse_to_ET_element(content)
    with raises(RequiredFieldNotFoundExtractionError):
        parser._publisher_specific_parsing(article)


def test_publication_info_fields_values_just_year(shared_datadir, parser):
    content = (
        shared_datadir / "no_journal_tiltle_volume_issue_artid_values.xml"
    ).read_text()
    article = ET.fromstring(content)
    with raises(RequiredFieldNotFoundExtractionError):
        parser._publisher_specific_parsing(article)


def test_no_license_url(shared_datadir, parser):
    content = (shared_datadir / "no_license_url.xml").read_text()
    article = ET.fromstring(content)
    with raises(RequiredFieldNotFoundExtractionError):
        parser._publisher_specific_parsing(article)


def test_collaborations(shared_datadir, parser):
    content = (shared_datadir / "all_fields.xml").read_text()
    article = ET.fromstring(content)
    parsed_article = parser._publisher_specific_parsing(article)
    assert parsed_article["collaborations"] == ["JNE collaboration"]


def test_no_collaborations(shared_datadir, parser):
    content = (shared_datadir / "just_required_fields.xml").read_text()
    article = ET.fromstring(content)
    parsed_article = parser._publisher_specific_parsing(article)
    assert "collaborations" not in parsed_article


def test_no_collaborations_value(shared_datadir, parser):
    content = (shared_datadir / "no_collaboration_value.xml").read_text()
    article = ET.fromstring(content)
    parsed_article = parser._publisher_specific_parsing(article)
    assert "collaborations" not in parsed_article


def test_title(shared_datadir, parser):  # noqa
    content = (shared_datadir / "just_required_fields.xml").read_text()
    article = ET.fromstring(content)
    parsed_article = parser._publisher_specific_parsing(article)
    assert (
        parsed_article["title"]
        == "Measurement of muon-induced neutron yield at the China Jinping Underground Laboratory"
        " * Supported in part by the National Natural Science Foundation of China (11620101004, "
        "11475093, 12127808), the Key Laboratory of Particle & Radiation Imaging (TsinghuaUniversity),"
        " the CAS Center for Excellence in Particle Physics (CCEPP), and Guangdong Basic and Applied "
        "Basic Research Foundation (2019A1515012216). Portion of this work performed at Brookhaven "
        "National Laboratory is supported in part by the United States Department of Energy (DE-SC0012704)"
    )


# Couldn't find original IOP articles, which have subtitle
# The data is falsified
def test_subtitle(shared_datadir, parser):
    content = (shared_datadir / "with_subtitle.xml").read_text()
    article = ET.fromstring(content)
    parsed_article = parser._publisher_specific_parsing(article)
    assert parsed_article["subtitle"] == "Subtitle (pseudo data)"


def test_no_title(shared_datadir, parser):
    content = (shared_datadir / "no_title.xml").read_text()
    article = parse_to_ET_element(content)
    with raises(RequiredFieldNotFoundExtractionError):
        parser._publisher_specific_parsing(article)


def test_no_subtitle(shared_datadir, parser):
    content = (shared_datadir / "just_required_fields.xml").read_text()
    article = ET.fromstring(content)
    parsed_article = parser._publisher_specific_parsing(article)
    assert "subtitle" not in parsed_article


def test_no_title_no_subtitle_values(shared_datadir, parser):
    content = (shared_datadir / "no_title_no_subtitle_values.xml").read_text()
    article = ET.fromstring(content)
    article = parse_to_ET_element(content)
    with raises(RequiredFieldNotFoundExtractionError):
        parser._publisher_specific_parsing(article)


def test_no_licenses_statement(shared_datadir, parser):
    content = (shared_datadir / "no_license_statement.xml").read_text()
    article = ET.fromstring(content)
    parsed_article = parser._publisher_specific_parsing(article)
    assert parsed_article["license"] == [
        {"license": "CC-BY-3.0", "url": "http://creativecommons.org/licenses/by/3.0/"}
    ]


def test_unknown_license_in_license_URL(shared_datadir, parser):
    content = (shared_datadir / "unknown_license_in_license_URL.xml").read_text()
    article = ET.fromstring(content)
    with raises(UnknownLicense):
        parser._publisher_specific_parsing(article)


def test_cdata_with_regex():
    paseudo_aricle = """
    <article>
        <title>That's the title</title>
    <abstract>
        <p><?CDATA Data in Cdata ?>Data not in CDATA</p>
    </abstract>
    </article>
    """
    ET_article = parse_to_ET_element(paseudo_aricle)
    abstract_element = ET_article.find("abstract/p")
    abstract_text = abstract_element.text
    assert abstract_text == " Data in Cdata Data not in CDATA"

    title_element = ET_article.find("title")
    title_text = title_element.text
    assert title_text == "That's the title"

    string_abstract = ET.tostring(abstract_element)
    assert string_abstract == b"<p> Data in Cdata Data not in CDATA</p>\n    "


def test_cdata_abstract_title(shared_datadir):
    content = (shared_datadir / "title_and_abstract_with_cdata.xml").read_text()
    content = replace_cdata_format(content)
    ET_article = parse_to_ET_element(content)

    abstract_element = ET_article.find("front/article-meta/abstract/p")
    abstract_text = parse_element_text(abstract_element)
    assert (
        abstract_text
        == "Recently, the experimental measurements of the branching ratios and different"
        " polarization asymmetries for processes occurring through flavor-changing-charged"
        " current $ (b\\rightarrow c\\tau\\overline{\\nu}_{\\tau}) $ transitions by BABAR,"
        " Belle, and LHCb have revealed some significant differences from the corresponding"
        " Standard Model (SM) predictions. This has triggered an interest to search for physics"
        " beyond the SM in the context of various new physics (NP) models and using the model-independent"
        " weak effective Hamiltonian (WEH). Assuming left-handed neutrinos, we add the dimension-six vector,"
        " (pseudo-)scalar, and tensor operators with complex Wilson coefficients (WCs) to the SM WEH. Using"
        " 60%, 30%, and 10% constraints resulting from the branching ratio of $ B_{c}\\to\\tau\\bar{\\nu}_{\\tau} $"
        " , we reassess the parametric space of these new physics WCs accommodating the current anomalies"
        " based on the most recent HFLAV data of $ R_{\\tau/{\\mu,e}}\\left(D\\right) $ and"
        " $ R_{\\tau/{\\mu,e}}\\left(D^*\\right) $ and Belle data of $ F_{L}\\left(D^*\\right) $"
        " and $ P_{\\tau}\\left(D^*\\right) $ . We find that the allowed parametric region of left-handed"
        " scalar couplings strongly depends on the constraints of the $ B_{c}\\rightarrow \\tau\\bar{\\nu}_{\\tau} $"
        " branching ratio, and the maximum pull from the SM predictions results from the <60% branching ratio limit."
        " Also, the parametric region changes significantly if we extend the analysis by adding LHCb data of "
        "$ R_{\\tau/\\mu}\\left(J/\\psi\\right) $ and $ R_{\\tau/\\ell}\\left(\\Lambda_c\\right) $ . Furthermore,"
        " due to the large uncertainties in the measurements of $ R_{\\tau/\\mu}\\left(J/\\psi\\right) $ and"
        " $ R_{\\tau/\\ell}\\left(X_c\\right) $ , we derive the sum rules which complement them with "
        "$ R_{\\tau/{\\mu,e}}\\left(D\\right) $ and $ R_{\\tau/{\\mu,e}}\\left(D^*\\right) $ . Using the"
        " best-fit points of the new complex WCs along with the latest measurements of "
        "$ R_{\\tau/{\\mu,e}}\\left(D^{(*)}\\right) $ , we predict the numerical values of the observable"
        " $ R_{\\tau/\\ell}\\left(\\Lambda_c\\right) $ , $ R_{\\tau/\\mu}\\left(J/\\psi\\right) $ , "
        "and $ R_{\\tau/\\ell}\\left(X_c\\right) $ from the sum rules. The simultaneous dependence of "
        "abovementioned physical observables on the NP WCs is established by plotting their correlation "
        "with $ R_{D} $ and $ R_{D^*} $ , which are useful to discriminate between various NP scenarios."
        " We find that the most significant impact of NP results from the WC $ C_{L}^{S}=4C^{T} $ . Finally,"
        " we study the impact of these NP couplings on various angular and $ CP $ triple product asymmetries"
        " that could be measured in some ongoing and future experiments. The precise measurements of these "
        "observables are important to check the SM and extract the possible NP."
    )
    title_element = ET_article.find("front/article-meta/title-group/article-title")
    title_text = parse_element_text(title_element)
    assert (
        title_text
        == "Analysis of ${{\\boldsymbol b}{\\bf\\rightarrow} {\\boldsymbol c}{\\boldsymbol\\tau}\\bar"
        "{\\boldsymbol\\nu}_{\\boldsymbol\\tau}}$ anomalies using weak effective Hamiltonian with "
        "complex couplings and their impact on various physical observables"
    )


def test_cdata_without_regex():
    paseudo_aricle = """
    <article>
        <title>That's the title</title>
    <abstract>
        <p><?CDATA Data in Cdata ?>Data not in CDATA</p>
    </abstract>
    </article>
    """
    ET_article = ET.fromstring(paseudo_aricle)
    p_element_content = ET.tostring(ET_article.find("abstract"))
    assert (
        p_element_content
        == b"<abstract>\n        <p>Data not in CDATA</p>\n    </abstract>\n    "
    )

    abstract_element = ET_article.find("abstract/p")
    abstract_text = abstract_element.text
    assert abstract_text == "Data not in CDATA"

    title_element = ET_article.find("title")
    title_text = title_element.text
    assert title_text == "That's the title"

    string_abstract = ET.tostring(abstract_element)
    assert string_abstract == b"<p>Data not in CDATA</p>\n    "


def test_title_starting_with_tags(shared_datadir, parser):
    content = (shared_datadir / "aca95c.xml").read_text()
    article = convert_xml_to_et_tree(content)

    parsed_article = parser._publisher_specific_parsing(article)
    assert (
        parsed_article["title"]
        == "$\\textit{R}$-Symmetric NMSSM * Supported in part by the National Natural Science Foundation of "
        "China (11775039), the High-level Talents Research and Startup Foundation Projects for Doctors of "
        "Zhoukou Normal University (ZKNUC2021006), and Scientific research projects of universities in"
        " Henan Province, China (23A140027)."
    )


def test_title_starting_with_tags_after_enhancer(shared_datadir, parser):
    content = (shared_datadir / "aca95c.xml").read_text()
    article = convert_xml_to_et_tree(content)

    parsed_article = parser.parse(article)
    enhanced_file = Enhancer()("IOP", parsed_article)
    assert (
        enhanced_file["titles"][0]["title"]
        == "$\\textit{R}$-Symmetric NMSSM * Supported in part by the National Natural Science Foundation of "
        "China (11775039), the High-level Talents Research and Startup Foundation Projects for Doctors of "
        "Zhoukou Normal University (ZKNUC2021006), and Scientific research projects of universities in"
        " Henan Province, China (23A140027)."
    )
