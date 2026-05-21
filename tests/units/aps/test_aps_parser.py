import json

import pytest
from aps.aps_process_file import enhance_aps
from aps.parser import APSParser


@pytest.fixture(scope="module")
def parser():
    return APSParser()


@pytest.fixture
def articles(shared_datadir):
    json_response = (shared_datadir / "json_response_content.json").read_text()
    return [article for article in json.loads(json_response)["data"]]


@pytest.fixture
def parsed_articles(parser, articles):
    return [parser._publisher_specific_parsing(article) for article in articles]


@pytest.mark.parametrize(
    ("expected", "key"),
    [
        pytest.param(
            [["10.1103/PhysRevA.103.042607"], ["10.1103/PhysRevB.103.165408"]],
            "dois",
            id="test_dois",
        ),
        pytest.param(["article", "article"], "journal_doctype", id="test_articleType"),
        pytest.param([[10], [11]], "page_nr", id="test_page_nr"),
        pytest.param(
            [[{"value": "2102.07212"}], [{"value": "2012.07847"}]],
            "arxiv_eprints",
            id="test_arxiv_eprints",
        ),
        pytest.param(
            [
                "<p>We propose and theoretically analyze the use of coherent population trapping of a single diamond nitrogen-vacancy (NV) center for continuous real-time sensing. The formation of the dark state in coherent population trapping prevents optical emissions from the NV center. Fluctuating magnetic fields, however, can kick the NV center out of the dark state, leading to a sequence of single-photon emissions. A time series of the photon counts detected can be used for magnetic field estimations, even when the average photon count per update time interval is much smaller than 1. For a theoretical demonstration, the nuclear spin bath in a diamond lattice is used as a model fluctuating magnetic environment. For fluctuations with known statistical properties, such as an Ornstein-Uhlenbeck process, Bayesian inference-based estimators can lead to an estimation variance that approaches the classical Cramer-Rao lower bound and can update dynamical information in real time with the detection of just a single photon. Real-time sensing using coherent population trapping adds a powerful tool to the emerging technology of quantum sensing.</p>",
                "<p>Recent advances in ultracold atoms in optical lattices and developments in surface science have allowed for the creation of artificial lattices as well as the control of many-body interactions. Such systems provide new settings to investigate interaction-driven instabilities and nontrivial topology. In this paper, we explore the interplay between molecular electric dipoles on a two-dimensional triangular lattice with fermions hopping on the dual decorated honeycomb lattice which hosts Dirac and flat band states. We show that short-range dipole-dipole interaction can lead to ordering into various stripe and vortex crystal ground states. We study these ordered states and their thermal transitions as a function of the interaction range using simulated annealing and Monte Carlo methods. For the special case of zero-wave-vector ferrodipolar order, incorporating dipole-electron interactions and integrating out the electrons leads to a six-state clock model for the dipole ordering. Finally, we discuss the impact of the various dipole orders on the electronic band structure and the local tunneling density of states. Our work may be relevant to studies of “molecular graphene”—CO molecules arranged on the Cu(111) surface—which have been explored using scanning tunneling spectroscopy, as well as ultracold molecule-fermion mixtures in optical lattices.</p>",
            ],
            "abstract",
            id="test_abstract",
        ),
        pytest.param(
            [
                "Continuous real-time sensing with a nitrogen-vacancy center via coherent population trapping",
                "Molecular dipoles in designer honeycomb lattices",
            ],
            "title",
            id="test_title",
        ),
        pytest.param(
            [
                [
                    {
                        "full_name": "Shu-Hao Wu",
                        "given_names": "Shu-Hao",
                        "surname": "Wu",
                        "affiliations": [
                            {
                                "value": 'Department of Physics and Astronomy, <a href="https://ror.org/02vm5rt34">Vanderbilt University</a>, Nashville, Tennessee 37240, USA',
                                "organization": "Department of Physics and Astronomy, Vanderbilt University",
                                "ror": "https://ror.org/02vm5rt34",
                            }
                        ],
                    },
                    {
                        "full_name": "Ethan Turner",
                        "given_names": "Ethan",
                        "surname": "Turner",
                        "affiliations": [
                            {
                                "value": 'Department of Physics and Astronomy, <a href="https://ror.org/02vm5rt34">Vanderbilt University</a>, Nashville, Tennessee 37240, USA',
                                "organization": "Department of Physics and Astronomy, Vanderbilt University",
                                "ror": "https://ror.org/02vm5rt34",
                            }
                        ],
                    },
                    {
                        "full_name": "Hailin Wang",
                        "given_names": "Hailin",
                        "surname": "Wang",
                        "affiliations": [
                            {
                                "value": 'Department of Physics and Astronomy, <a href="https://ror.org/02vm5rt34">Vanderbilt University</a>, Nashville, Tennessee 37240, USA',
                                "organization": "Department of Physics and Astronomy, Vanderbilt University",
                                "ror": "https://ror.org/02vm5rt34",
                            }
                        ],
                    },
                    {
                        "full_name": "Tim R. Borel",
                        "given_names": "Tim R.",
                        "surname": "Borel",
                        "affiliations": [
                            {
                                "value": 'Department of Physics and Astronomy, <a href="https://ror.org/02vm5rt34">Vanderbilt University</a>, Nashville, Tennessee 37240, USA',
                                "organization": "Department of Physics and Astronomy, Vanderbilt University",
                                "ror": "https://ror.org/02vm5rt34",
                            }
                        ],
                    },
                ],
                [
                    {
                        "full_name": "Nazim Boudjada",
                        "given_names": "Nazim",
                        "surname": "Boudjada",
                        "affiliations": [
                            {
                                "value": 'Department of Physics and Astronomy, <a href="https://ror.org/02vm5rt34">Vanderbilt University</a>, Nashville, Tennessee 37240, USA',
                                "organization": "Department of Physics and Astronomy, Vanderbilt University",
                                "ror": "https://ror.org/02vm5rt34",
                            }
                        ],
                    },
                    {
                        "full_name": "Finn Lasse Buessen",
                        "given_names": "Finn Lasse",
                        "surname": "Buessen",
                        "affiliations": [
                            {
                                "value": 'Department of Physics and Astronomy, <a href="https://ror.org/02vm5rt34">Vanderbilt University</a>, Nashville, Tennessee 37240, USA',
                                "organization": "Department of Physics and Astronomy, Vanderbilt University",
                                "ror": "https://ror.org/02vm5rt34",
                            }
                        ],
                    },
                    {
                        "full_name": "Arun Paramekanti",
                        "given_names": "Arun",
                        "surname": "Paramekanti",
                        "affiliations": [
                            {
                                "value": 'Department of Physics and Astronomy, <a href="https://ror.org/02vm5rt34">Vanderbilt University</a>, Nashville, Tennessee 37240, USA',
                                "organization": "Department of Physics and Astronomy, Vanderbilt University",
                                "ror": "https://ror.org/02vm5rt34",
                            }
                        ],
                    },
                ],
            ],
            "authors",
            id="test_authors",
        ),
        pytest.param(
            ["Physical Review A", "Physical Review B"],
            "journal_title",
            id="test_journal_title",
        ),
        pytest.param(["4", "16"], "journal_issue", id="test_journal_issue"),
        pytest.param(["103", "103"], "journal_volume", id="test_journal_volume"),
        pytest.param([2021, 2021], "journal_year", id="test_journal_year"),
        pytest.param(
            ["2021-04-12", "2021-04-12"], "date_published", id="test_date_published"
        ),
        pytest.param(
            ["American Physical Society", "American Physical Society"],
            "copyright_holder",
            id="test_copyright_holderd",
        ),
        pytest.param([2021, 2021], "copyright_year", id="test_copyright_year"),
        pytest.param(
            ["©2021 American Physical Society", "©2021 American Physical Society"],
            "copyright_statement",
            id="test_copyright_statement",
        ),
        pytest.param(
            [
                [
                    {
                        "license": "CC-BY-3.0",
                        "url": "http://link.aps.org/licenses/aps-default-license",
                    }
                ],
                [
                    {
                        "license": "CC-BY-3.0",
                        "url": "http://link.aps.org/licenses/aps-default-license",
                    }
                ],
            ],
            "license",
            id="test_license",
        ),
        pytest.param([[], []], "field_categories", id="test_field_categories"),
        pytest.param(
            [["HEP", "Citeable", "Published"], ["HEP", "Citeable", "Published"]],
            "collections",
            id="test_collections",
        ),
    ],
)
def test_aps_parsing(parsed_articles, expected, key):
    for (
        expected_value,
        article,
    ) in zip(expected, parsed_articles, strict=False):
        assert key in article
        assert article[key] == expected_value


def test_aps_country_parsing(parsed_articles):
    for article in parsed_articles:
        enhance_aps(article)
