import pytest
from common.enhancer import Enhancer
from freezegun import freeze_time

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
input_with_affiliation_of_cooperation_agreement_with_CERN = {
    "abstract": "this is abstracts",
    "authors": [
        {
            "affiliations": [
                {
                    "country": "Switzerland",
                    "organization": "International laboratory covered by a cooperation agreement with CERN",
                    "value": "International laboratory covered by a cooperation agreement with CERN, Geneva, Switzerland",
                }
            ],
            "email": "test@email.com",
            "full_name": "Test Surname, Test names",
            "given_names": "Test names",
            "surname": "Test Surname",
            "orcid": "Test Id",
        }
    ],
    "copyright_holder": "copyright_holder",
    "copyright_year": "2020",
    "copyright_statement": "copyright_statement",
    "copyright_material": "copyright_material",
    "date_published": "2022-05-20",
    "title": "title",
    "subtitle": "subtitle",
}
input_with_affiliation_of_cooperation_agreement_with_CERN_no_country = {
    "abstract": "this is abstracts",
    "authors": [
        {
            "affiliations": [
                {
                    "organization": "International laboratory covered by a cooperation agreement with CERN",
                    "value": "International laboratory covered by a cooperation agreement with CERN, Geneva, Switzerland",
                }
            ],
            "email": "test@email.com",
            "full_name": "Test Surname, Test names",
            "given_names": "Test names",
            "surname": "Test Surname",
            "orcid": "Test Id",
        }
    ],
    "copyright_holder": "copyright_holder",
    "copyright_year": "2020",
    "copyright_statement": "copyright_statement",
    "copyright_material": "copyright_material",
    "date_published": "2022-05-20",
    "title": "title",
    "subtitle": "subtitle",
}
expected_output_with_affiliation_of_cooperation_agreement_with_CERN = {
    "abstracts": [{"value": "this is abstracts", "source": publisher}],
    "authors": [
        {
            "affiliations": [
                {
                    "organization": "International laboratory covered by a cooperation agreement with CERN",
                    "value": "International laboratory covered by a cooperation agreement with CERN, Geneva, Switzerland",
                }
            ],
            "email": "test@email.com",
            "full_name": "Test Surname, Test names",
            "given_names": "Test names",
            "surname": "Test Surname",
            "orcid": "Test Id",
        }
    ],
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

input_with_correct_affiliation = {
    "abstract": "this is abstracts",
    "authors": [
        {
            "affiliations": [
                {
                    "country": "Switzerland",
                    "organization": "CERN",
                    "value": "CERN, Geneva, Switzerland",
                }
            ],
            "email": "test@email.com",
            "full_name": "Test Surname, Test names",
            "given_names": "Test names",
            "surname": "Test Surname",
            "orcid": "Test Id",
        }
    ],
    "copyright_holder": "copyright_holder",
    "copyright_year": "2020",
    "copyright_statement": "copyright_statement",
    "copyright_material": "copyright_material",
    "date_published": "2022-05-20",
    "title": "title",
    "subtitle": "subtitle",
}
output_with_correct_affiliation = {
    "abstracts": [{"value": "this is abstracts", "source": publisher}],
    "authors": [
        {
            "affiliations": [
                {
                    "country": "Switzerland",
                    "organization": "CERN",
                    "value": "CERN, Geneva, Switzerland",
                }
            ],
            "email": "test@email.com",
            "full_name": "Test Surname, Test names",
            "given_names": "Test names",
            "surname": "Test Surname",
            "orcid": "Test Id",
        }
    ],
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
input_with_affiliation_value_only = {
    "abstract": "this is abstracts",
    "authors": [
        {
            "affiliations": [
                {
                    "value": "Department of Physics, Tsinghua University, Beijing 100084",
                    "organization": "Department of Physics, Tsinghua University",
                }
            ],
            "email": "test@email.com",
            "full_name": "Test Surname, Test names",
            "given_names": "Test names",
            "surname": "Test Surname",
            "orcid": "Test Id",
        }
    ],
    "copyright_holder": "copyright_holder",
    "copyright_year": "2020",
    "copyright_statement": "copyright_statement",
    "copyright_material": "copyright_material",
    "date_published": "2022-05-20",
    "title": "title",
    "subtitle": "subtitle",
}
expected_output_with_affiliation_value_only = {
    "abstracts": [{"value": "this is abstracts", "source": publisher}],
    "authors": [
        {
            "affiliations": [
                {
                    "value": "Department of Physics, Tsinghua University, Beijing 100084",
                    "organization": "Department of Physics, Tsinghua University",
                    "country": "China",
                }
            ],
            "email": "test@email.com",
            "full_name": "Test Surname, Test names",
            "given_names": "Test names",
            "surname": "Test Surname",
            "orcid": "Test Id",
        }
    ],
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

wrong_author_affiliation = {
    "dois": [{"value": "10.1103/PhysRevD.108.072002"}],
    "page_nr": [16],
    "arxiv_eprints": [{"value": "2307.09427"}],
    "abstract": '<p>The decay <math xmlns="http://www.w3.org/1998/Math/MathML" display="inline"><msubsup><mi mathvariant="normal">Ξ</mi><mi>b</mi><mo>−</mo></msubsup><mo stretchy="false">→</mo><msubsup><mi mathvariant="normal">Λ</mi><mi>b</mi><mn>0</mn></msubsup><msup><mi>π</mi><mo>−</mo></msup></math> is observed using a proton-proton collision data sample collected at center-of-mass energy <math xmlns="http://www.w3.org/1998/Math/MathML" display="inline"><msqrt><mi>s</mi></msqrt><mo>=</mo><mn>13</mn><mtext> </mtext><mtext> </mtext><mi>TeV</mi></math> with the LHCb detector, corresponding to an integrated luminosity of <math xmlns="http://www.w3.org/1998/Math/MathML" display="inline"><mn>5.5</mn><mtext> </mtext><mtext> </mtext><msup><mi>fb</mi><mrow><mo>−</mo><mn>1</mn></mrow></msup></math>. This process is mediated by the <math xmlns="http://www.w3.org/1998/Math/MathML" display="inline"><mi>s</mi><mo stretchy="false">→</mo><mi>u</mi><mover accent="true"><mi>u</mi><mo stretchy="false">¯</mo></mover><mi>d</mi></math> quark-level transition, where the <math xmlns="http://www.w3.org/1998/Math/MathML" display="inline"><mi>b</mi></math> quark in the <math xmlns="http://www.w3.org/1998/Math/MathML" display="inline"><msubsup><mi mathvariant="normal">Ξ</mi><mi>b</mi><mo>−</mo></msubsup></math> baryon is a spectator in the decay. Averaging the results obtained using the two <math xmlns="http://www.w3.org/1998/Math/MathML" display="inline"><msubsup><mi mathvariant="normal">Λ</mi><mi>b</mi><mn>0</mn></msubsup></math> decay modes, <math xmlns="http://www.w3.org/1998/Math/MathML" display="inline"><msubsup><mi mathvariant="normal">Λ</mi><mi>b</mi><mn>0</mn></msubsup><mo stretchy="false">→</mo><msubsup><mi mathvariant="normal">Λ</mi><mi>c</mi><mo>+</mo></msubsup><msup><mi>π</mi><mo>−</mo></msup></math> and <math xmlns="http://www.w3.org/1998/Math/MathML" display="inline"><msubsup><mi mathvariant="normal">Λ</mi><mi>b</mi><mn>0</mn></msubsup><mo stretchy="false">→</mo><msubsup><mi mathvariant="normal">Λ</mi><mi>c</mi><mo>+</mo></msubsup><msup><mi>π</mi><mo>−</mo></msup><msup><mi>π</mi><mo>+</mo></msup><msup><mi>π</mi><mo>−</mo></msup></math>, the relative production ratio is measured to be <math xmlns="http://www.w3.org/1998/Math/MathML" display="inline"><mo stretchy="false">(</mo><msub><mi>f</mi><msubsup><mi mathvariant="normal">Ξ</mi><mi>b</mi><mo>−</mo></msubsup></msub><mo stretchy="false">/</mo><msub><mi>f</mi><msubsup><mi mathvariant="normal">Λ</mi><mi>b</mi><mn>0</mn></msubsup></msub><mo stretchy="false">)</mo><mi mathvariant="script">B</mi><mo stretchy="false">(</mo><msubsup><mi mathvariant="normal">Ξ</mi><mi>b</mi><mo>−</mo></msubsup><mo stretchy="false">→</mo><msubsup><mi mathvariant="normal">Λ</mi><mi>b</mi><mn>0</mn></msubsup><msup><mi>π</mi><mo>−</mo></msup><mo stretchy="false">)</mo><mo>=</mo><mspace linebreak="goodbreak"></mspace><mo stretchy="false">(</mo><mn>7.3</mn><mo>±</mo><mn>0.8</mn><mo>±</mo><mn>0.6</mn><mo stretchy="false">)</mo><mo>×</mo><msup><mn>10</mn><mrow><mo>−</mo><mn>4</mn></mrow></msup></math>. Here the uncertainties are statistical and systematic, respectively, and <math xmlns="http://www.w3.org/1998/Math/MathML" display="inline"><msub><mi>f</mi><msubsup><mi mathvariant="normal">Ξ</mi><mi>b</mi><mo>−</mo></msubsup></msub><mo stretchy="false">(</mo><msub><mi>f</mi><msubsup><mi mathvariant="normal">Λ</mi><mi>b</mi><mn>0</mn></msubsup></msub><mo stretchy="false">)</mo></math> is the fragmentation fraction for a <math xmlns="http://www.w3.org/1998/Math/MathML" display="inline"><mi>b</mi></math> quark into a <math xmlns="http://www.w3.org/1998/Math/MathML" display="inline"><msubsup><mi mathvariant="normal">Ξ</mi><mi>b</mi><mo>−</mo></msubsup></math> (<math xmlns="http://www.w3.org/1998/Math/MathML" display="inline"><msubsup><mi mathvariant="normal">Λ</mi><mi>b</mi><mn>0</mn></msubsup></math>) baryon. Using an independent measurement of <math xmlns="http://www.w3.org/1998/Math/MathML" display="inline"><msub><mi>f</mi><msubsup><mi mathvariant="normal">Ξ</mi><mi>b</mi><mo>−</mo></msubsup></msub><mo stretchy="false">/</mo><msub><mi>f</mi><msubsup><mi mathvariant="normal">Λ</mi><mi>b</mi><mn>0</mn></msubsup></msub></math>, the branching fraction <math xmlns="http://www.w3.org/1998/Math/MathML" display="inline"><mi mathvariant="script">B</mi><mo stretchy="false">(</mo><msubsup><mi mathvariant="normal">Ξ</mi><mi>b</mi><mo>−</mo></msubsup><mo stretchy="false">→</mo><msubsup><mi mathvariant="normal">Λ</mi><mi>b</mi><mn>0</mn></msubsup><msup><mi>π</mi><mo>−</mo></msup><mo stretchy="false">)</mo><mo>=</mo><mo stretchy="false">(</mo><mn>0.89</mn><mo>±</mo><mn>0.10</mn><mo>±</mo><mn>0.07</mn><mo>±</mo><mn>0.29</mn><mo stretchy="false">)</mo><mo>%</mo></math> is obtained, where the last uncertainty is due to the assumed SU(3) flavor symmetry in the determination of <math xmlns="http://www.w3.org/1998/Math/MathML" display="inline"><msub><mi>f</mi><msubsup><mi mathvariant="normal">Ξ</mi><mi>b</mi><mo>−</mo></msubsup></msub><mo stretchy="false">/</mo><msub><mi>f</mi><msubsup><mi mathvariant="normal">Λ</mi><mi>b</mi><mn>0</mn></msubsup></msub></math>.</p>',
    "title": 'Observation and branching fraction measurement of the decay <math xmlns="http://www.w3.org/1998/Math/MathML" display="inline"><msubsup><mi mathvariant="normal">Ξ</mi><mi>b</mi><mo>−</mo></msubsup><mo stretchy="false">→</mo><msubsup><mi mathvariant="normal">Λ</mi><mi>b</mi><mn>0</mn></msubsup><msup><mi>π</mi><mo>−</mo></msup></math>',
    "authors": [
        {
            "full_name": "Jaimes Elles, S.J.",
            "given_names": "S.J.",
            "surname": "Jaimes Elles",
            "affiliations": [
                {
                    "value": "Instituto de Fisica Corpuscular, Centro Mixto Universidad de Valencia—CSIC, Valencia, Spain",
                    "organization": "Instituto de Fisica Corpuscular, Centro Mixto Universidad de Valencia—CSIC, Valencia",
                },
                {
                    "value": "Departamento de Fisica, Universidad Nacional de Colombia, Bogota, Colombia (associated with LPNHE, Sorbonne Université, Paris Diderot Sorbonne Paris Cité, CNRS/IN2P3, Paris, France)",
                    "organization": "Departamento de Fisica, Universidad Nacional de Colombia, Bogota, Colombia (associated with LPNHE, Sorbonne Université, Paris Diderot Sorbonne Paris Cité, CNRS/IN2P3, Paris",
                },
            ],
        },
        {
            "full_name": "Jakobsen, S.",
            "given_names": "S.",
            "surname": "Jakobsen",
            "affiliations": [
                {
                    "value": "European Organization for Nuclear Research (CERN), Geneva, Switzerland",
                    "organization": "European Organization for Nuclear Research (CERN), Geneva",
                }
            ],
        },
        {
            "full_name": "Jashal, B.K.",
            "given_names": "B.K.",
            "surname": "Jashal",
            "affiliations": [
                {
                    "value": "Instituto de Fisica Corpuscular, Centro Mixto Universidad de Valencia—CSIC, Valencia, Spain",
                    "organization": "Instituto de Fisica Corpuscular, Centro Mixto Universidad de Valencia—CSIC, Valencia",
                }
            ],
        },
        {
            "full_name": "Jawahery, A.",
            "given_names": "A.",
            "surname": "Jawahery",
            "affiliations": [
                {
                    "value": "University of Maryland, College Park, Maryland, USA",
                    "organization": "University of Maryland, College Park, Maryland",
                }
            ],
        },
        {
            "full_name": "Jevtic, V.",
            "given_names": "V.",
            "surname": "Jevtic",
            "affiliations": [
                {
                    "value": "Fakultät Physik, Technische Universität Dortmund, Dortmund, Germany",
                    "organization": "Fakultät Physik, Technische Universität Dortmund, Dortmund",
                }
            ],
        },
        {
            "full_name": "Kulikova, E.",
            "given_names": "E.",
            "surname": "Kulikova",
            "affiliations": [
                {
                    "value": "Affiliated with an institute covered by a cooperation agreement with CERN"
                }
            ],
        },
        {
            "full_name": "Kupsc, A.",
            "given_names": "A.",
            "surname": "Kupsc",
            "affiliations": [
                {
                    "value": "Department of Physics and Astronomy, Uppsala University, Uppsala, Sweden (associated with School of Physics and Astronomy, University of Glasgow, Glasgow, United Kingdom)",
                    "organization": "Department of Physics and Astronomy, Uppsala University, Uppsala, Sweden (associated with School of Physics and Astronomy, University of Glasgow, Glasgow",
                }
            ],
        },
        {
            "full_name": "Kutsenko, B.K.",
            "given_names": "B.K.",
            "surname": "Kutsenko",
            "affiliations": [
                {
                    "value": "Aix Marseille Université, CNRS/IN2P3, CPPM, Marseille, France",
                    "organization": "Aix Marseille Université, CNRS/IN2P3, CPPM, Marseille",
                }
            ],
        },
    ],
    "date_published": "2023-10-06",
    "copyright_holder": "CERN",
    "copyright_year": 2023,
    "copyright_statement": "© 2023 CERN, for the LHCb Collaboration",
    "license": [
        {"url": "https://creativecommons.org/licenses/by/4.0/", "license": "CC-BY-4.0"}
    ],
    "collections": [
        {"primary": "HEP"},
        {"primary": "Citeable"},
        {"primary": "Published"},
    ],
    "publication_info": [
        {
            "journal_title": "Physical Review D",
            "journal_volume": "108",
            "year": 2023,
            "journal_issue": "7",
            "material": "article",
        }
    ],
}

expected_wrong_author_affiliation = {
    "dois": [{"value": "10.1103/PhysRevD.108.072002"}],
    "page_nr": [16],
    "arxiv_eprints": [{"value": "2307.09427"}],
    "abstracts": [
        {
            "source": "Springer",
            "value": '<p>The decay <math xmlns="http://www.w3.org/1998/Math/MathML" display="inline"><msubsup><mi mathvariant="normal">Ξ</mi><mi>b</mi><mo>−</mo></msubsup><mo stretchy="false">→</mo><msubsup><mi mathvariant="normal">Λ</mi><mi>b</mi><mn>0</mn></msubsup><msup><mi>π</mi><mo>−</mo></msup></math> is observed using a proton-proton collision data sample collected at center-of-mass energy <math xmlns="http://www.w3.org/1998/Math/MathML" display="inline"><msqrt><mi>s</mi></msqrt><mo>=</mo><mn>13</mn><mtext> </mtext><mtext> </mtext><mi>TeV</mi></math> with the LHCb detector, corresponding to an integrated luminosity of <math xmlns="http://www.w3.org/1998/Math/MathML" display="inline"><mn>5.5</mn><mtext> </mtext><mtext> </mtext><msup><mi>fb</mi><mrow><mo>−</mo><mn>1</mn></mrow></msup></math>. This process is mediated by the <math xmlns="http://www.w3.org/1998/Math/MathML" display="inline"><mi>s</mi><mo stretchy="false">→</mo><mi>u</mi><mover accent="true"><mi>u</mi><mo stretchy="false">¯</mo></mover><mi>d</mi></math> quark-level transition, where the <math xmlns="http://www.w3.org/1998/Math/MathML" display="inline"><mi>b</mi></math> quark in the <math xmlns="http://www.w3.org/1998/Math/MathML" display="inline"><msubsup><mi mathvariant="normal">Ξ</mi><mi>b</mi><mo>−</mo></msubsup></math> baryon is a spectator in the decay. Averaging the results obtained using the two <math xmlns="http://www.w3.org/1998/Math/MathML" display="inline"><msubsup><mi mathvariant="normal">Λ</mi><mi>b</mi><mn>0</mn></msubsup></math> decay modes, <math xmlns="http://www.w3.org/1998/Math/MathML" display="inline"><msubsup><mi mathvariant="normal">Λ</mi><mi>b</mi><mn>0</mn></msubsup><mo stretchy="false">→</mo><msubsup><mi mathvariant="normal">Λ</mi><mi>c</mi><mo>+</mo></msubsup><msup><mi>π</mi><mo>−</mo></msup></math> and <math xmlns="http://www.w3.org/1998/Math/MathML" display="inline"><msubsup><mi mathvariant="normal">Λ</mi><mi>b</mi><mn>0</mn></msubsup><mo stretchy="false">→</mo><msubsup><mi mathvariant="normal">Λ</mi><mi>c</mi><mo>+</mo></msubsup><msup><mi>π</mi><mo>−</mo></msup><msup><mi>π</mi><mo>+</mo></msup><msup><mi>π</mi><mo>−</mo></msup></math>, the relative production ratio is measured to be <math xmlns="http://www.w3.org/1998/Math/MathML" display="inline"><mo stretchy="false">(</mo><msub><mi>f</mi><msubsup><mi mathvariant="normal">Ξ</mi><mi>b</mi><mo>−</mo></msubsup></msub><mo stretchy="false">/</mo><msub><mi>f</mi><msubsup><mi mathvariant="normal">Λ</mi><mi>b</mi><mn>0</mn></msubsup></msub><mo stretchy="false">)</mo><mi mathvariant="script">B</mi><mo stretchy="false">(</mo><msubsup><mi mathvariant="normal">Ξ</mi><mi>b</mi><mo>−</mo></msubsup><mo stretchy="false">→</mo><msubsup><mi mathvariant="normal">Λ</mi><mi>b</mi><mn>0</mn></msubsup><msup><mi>π</mi><mo>−</mo></msup><mo stretchy="false">)</mo><mo>=</mo><mspace linebreak="goodbreak"></mspace><mo stretchy="false">(</mo><mn>7.3</mn><mo>±</mo><mn>0.8</mn><mo>±</mo><mn>0.6</mn><mo stretchy="false">)</mo><mo>×</mo><msup><mn>10</mn><mrow><mo>−</mo><mn>4</mn></mrow></msup></math>. Here the uncertainties are statistical and systematic, respectively, and <math xmlns="http://www.w3.org/1998/Math/MathML" display="inline"><msub><mi>f</mi><msubsup><mi mathvariant="normal">Ξ</mi><mi>b</mi><mo>−</mo></msubsup></msub><mo stretchy="false">(</mo><msub><mi>f</mi><msubsup><mi mathvariant="normal">Λ</mi><mi>b</mi><mn>0</mn></msubsup></msub><mo stretchy="false">)</mo></math> is the fragmentation fraction for a <math xmlns="http://www.w3.org/1998/Math/MathML" display="inline"><mi>b</mi></math> quark into a <math xmlns="http://www.w3.org/1998/Math/MathML" display="inline"><msubsup><mi mathvariant="normal">Ξ</mi><mi>b</mi><mo>−</mo></msubsup></math> (<math xmlns="http://www.w3.org/1998/Math/MathML" display="inline"><msubsup><mi mathvariant="normal">Λ</mi><mi>b</mi><mn>0</mn></msubsup></math>) baryon. Using an independent measurement of <math xmlns="http://www.w3.org/1998/Math/MathML" display="inline"><msub><mi>f</mi><msubsup><mi mathvariant="normal">Ξ</mi><mi>b</mi><mo>−</mo></msubsup></msub><mo stretchy="false">/</mo><msub><mi>f</mi><msubsup><mi mathvariant="normal">Λ</mi><mi>b</mi><mn>0</mn></msubsup></msub></math>, the branching fraction <math xmlns="http://www.w3.org/1998/Math/MathML" display="inline"><mi mathvariant="script">B</mi><mo stretchy="false">(</mo><msubsup><mi mathvariant="normal">Ξ</mi><mi>b</mi><mo>−</mo></msubsup><mo stretchy="false">→</mo><msubsup><mi mathvariant="normal">Λ</mi><mi>b</mi><mn>0</mn></msubsup><msup><mi>π</mi><mo>−</mo></msup><mo stretchy="false">)</mo><mo>=</mo><mo stretchy="false">(</mo><mn>0.89</mn><mo>±</mo><mn>0.10</mn><mo>±</mo><mn>0.07</mn><mo>±</mo><mn>0.29</mn><mo stretchy="false">)</mo><mo>%</mo></math> is obtained, where the last uncertainty is due to the assumed SU(3) flavor symmetry in the determination of <math xmlns="http://www.w3.org/1998/Math/MathML" display="inline"><msub><mi>f</mi><msubsup><mi mathvariant="normal">Ξ</mi><mi>b</mi><mo>−</mo></msubsup></msub><mo stretchy="false">/</mo><msub><mi>f</mi><msubsup><mi mathvariant="normal">Λ</mi><mi>b</mi><mn>0</mn></msubsup></msub></math>.</p>',
        }
    ],
    "titles": [
        {
            "source": "Springer",
            "subtitle": "",
            "title": 'Observation and branching fraction measurement of the decay <math xmlns="http://www.w3.org/1998/Math/MathML" display="inline"><msubsup><mi mathvariant="normal">Ξ</mi><mi>b</mi><mo>−</mo></msubsup><mo stretchy="false">→</mo><msubsup><mi mathvariant="normal">Λ</mi><mi>b</mi><mn>0</mn></msubsup><msup><mi>π</mi><mo>−</mo></msup></math>',
        }
    ],
    "authors": [
        {
            "full_name": "Jaimes Elles, S.J.",
            "given_names": "S.J.",
            "surname": "Jaimes Elles",
            "affiliations": [
                {
                    "value": "Instituto de Fisica Corpuscular, Centro Mixto Universidad de Valencia—CSIC, Valencia, Spain",
                    "organization": "Instituto de Fisica Corpuscular, Centro Mixto Universidad de Valencia—CSIC, Valencia",
                    "country": "Spain",
                },
                {
                    "value": "Departamento de Fisica, Universidad Nacional de Colombia, Bogota, Colombia (associated with LPNHE, Sorbonne Université, Paris Diderot Sorbonne Paris Cité, CNRS/IN2P3, Paris, France)",
                    "organization": "Departamento de Fisica, Universidad Nacional de Colombia, Bogota, Colombia (associated with LPNHE, Sorbonne Université, Paris Diderot Sorbonne Paris Cité, CNRS/IN2P3, Paris",
                    "country": "France",
                },
            ],
        },
        {
            "full_name": "Jakobsen, S.",
            "given_names": "S.",
            "surname": "Jakobsen",
            "affiliations": [
                {
                    "value": "European Organization for Nuclear Research (CERN), Geneva, Switzerland",
                    "organization": "European Organization for Nuclear Research (CERN), Geneva",
                    "country": "CERN",
                }
            ],
        },
        {
            "full_name": "Jashal, B.K.",
            "given_names": "B.K.",
            "surname": "Jashal",
            "affiliations": [
                {
                    "value": "Instituto de Fisica Corpuscular, Centro Mixto Universidad de Valencia—CSIC, Valencia, Spain",
                    "organization": "Instituto de Fisica Corpuscular, Centro Mixto Universidad de Valencia—CSIC, Valencia",
                    "country": "Spain",
                }
            ],
        },
        {
            "full_name": "Jawahery, A.",
            "given_names": "A.",
            "surname": "Jawahery",
            "affiliations": [
                {
                    "value": "University of Maryland, College Park, Maryland, USA",
                    "organization": "University of Maryland, College Park, Maryland",
                    "country": "USA",
                }
            ],
        },
        {
            "full_name": "Jevtic, V.",
            "given_names": "V.",
            "surname": "Jevtic",
            "affiliations": [
                {
                    "value": "Fakultät Physik, Technische Universität Dortmund, Dortmund, Germany",
                    "organization": "Fakultät Physik, Technische Universität Dortmund, Dortmund",
                    "country": "Germany",
                }
            ],
        },
        {
            "full_name": "Kulikova, E.",
            "given_names": "E.",
            "surname": "Kulikova",
            "affiliations": [
                {
                    "value": "Affiliated with an institute covered by a cooperation agreement with CERN",
                }
            ],
        },
        {
            "full_name": "Kupsc, A.",
            "given_names": "A.",
            "surname": "Kupsc",
            "affiliations": [
                {
                    "value": "Department of Physics and Astronomy, Uppsala University, Uppsala, Sweden (associated with School of Physics and Astronomy, University of Glasgow, Glasgow, United Kingdom)",
                    "organization": "Department of Physics and Astronomy, Uppsala University, Uppsala, Sweden (associated with School of Physics and Astronomy, University of Glasgow, Glasgow",
                    "country": "Sweden",
                }
            ],
        },
        {
            "full_name": "Kutsenko, B.K.",
            "given_names": "B.K.",
            "surname": "Kutsenko",
            "affiliations": [
                {
                    "value": "Aix Marseille Université, CNRS/IN2P3, CPPM, Marseille, France",
                    "organization": "Aix Marseille Université, CNRS/IN2P3, CPPM, Marseille",
                    "country": "France",
                }
            ],
        },
    ],
    "imprints": [{"date": "2023-10-06", "publisher": "Springer"}],
    "copyright": [
        {
            "holder": "CERN",
            "material": "",
            "year": 2023,
            "statement": "© 2023 CERN, for the LHCb Collaboration",
        }
    ],
    "license": [
        {"url": "https://creativecommons.org/licenses/by/4.0/", "license": "CC-BY-4.0"}
    ],
    "collections": [
        {"primary": "HEP"},
        {"primary": "Citeable"},
        {"primary": "Published"},
    ],
    "publication_info": [
        {
            "journal_title": "Physical Review D",
            "journal_volume": "108",
            "year": 2023,
            "journal_issue": "7",
            "material": "article",
        },
    ],
    "acquisition_source": {
        "date": "2022-05-20T00:00:00",
        "method": "Springer",
        "source": "Springer",
    },
    "record_creation_date": "2022-05-20T00:00:00",
}

wrong_author_affiliation_2 = {
    "dois": [{"value": "10.1103/PhysRevD.108.072002"}],
    "page_nr": [16],
    "arxiv_eprints": [{"value": "2307.09427"}],
    "abstract": '<p>The decay <math xmlns="http://www.w3.org/1998/Math/MathML" display="inline"><msubsup><mi mathvariant="normal">Ξ</mi><mi>b</mi><mo>−</mo></msubsup><mo stretchy="false">→</mo><msubsup><mi mathvariant="normal">Λ</mi><mi>b</mi><mn>0</mn></msubsup><msup><mi>π</mi><mo>−</mo></msup></math> is observed using a proton-proton collision data sample collected at center-of-mass energy <math xmlns="http://www.w3.org/1998/Math/MathML" display="inline"><msqrt><mi>s</mi></msqrt><mo>=</mo><mn>13</mn><mtext> </mtext><mtext> </mtext><mi>TeV</mi></math> with the LHCb detector, corresponding to an integrated luminosity of <math xmlns="http://www.w3.org/1998/Math/MathML" display="inline"><mn>5.5</mn><mtext> </mtext><mtext> </mtext><msup><mi>fb</mi><mrow><mo>−</mo><mn>1</mn></mrow></msup></math>. This process is mediated by the <math xmlns="http://www.w3.org/1998/Math/MathML" display="inline"><mi>s</mi><mo stretchy="false">→</mo><mi>u</mi><mover accent="true"><mi>u</mi><mo stretchy="false">¯</mo></mover><mi>d</mi></math> quark-level transition, where the <math xmlns="http://www.w3.org/1998/Math/MathML" display="inline"><mi>b</mi></math> quark in the <math xmlns="http://www.w3.org/1998/Math/MathML" display="inline"><msubsup><mi mathvariant="normal">Ξ</mi><mi>b</mi><mo>−</mo></msubsup></math> baryon is a spectator in the decay. Averaging the results obtained using the two <math xmlns="http://www.w3.org/1998/Math/MathML" display="inline"><msubsup><mi mathvariant="normal">Λ</mi><mi>b</mi><mn>0</mn></msubsup></math> decay modes, <math xmlns="http://www.w3.org/1998/Math/MathML" display="inline"><msubsup><mi mathvariant="normal">Λ</mi><mi>b</mi><mn>0</mn></msubsup><mo stretchy="false">→</mo><msubsup><mi mathvariant="normal">Λ</mi><mi>c</mi><mo>+</mo></msubsup><msup><mi>π</mi><mo>−</mo></msup></math> and <math xmlns="http://www.w3.org/1998/Math/MathML" display="inline"><msubsup><mi mathvariant="normal">Λ</mi><mi>b</mi><mn>0</mn></msubsup><mo stretchy="false">→</mo><msubsup><mi mathvariant="normal">Λ</mi><mi>c</mi><mo>+</mo></msubsup><msup><mi>π</mi><mo>−</mo></msup><msup><mi>π</mi><mo>+</mo></msup><msup><mi>π</mi><mo>−</mo></msup></math>, the relative production ratio is measured to be <math xmlns="http://www.w3.org/1998/Math/MathML" display="inline"><mo stretchy="false">(</mo><msub><mi>f</mi><msubsup><mi mathvariant="normal">Ξ</mi><mi>b</mi><mo>−</mo></msubsup></msub><mo stretchy="false">/</mo><msub><mi>f</mi><msubsup><mi mathvariant="normal">Λ</mi><mi>b</mi><mn>0</mn></msubsup></msub><mo stretchy="false">)</mo><mi mathvariant="script">B</mi><mo stretchy="false">(</mo><msubsup><mi mathvariant="normal">Ξ</mi><mi>b</mi><mo>−</mo></msubsup><mo stretchy="false">→</mo><msubsup><mi mathvariant="normal">Λ</mi><mi>b</mi><mn>0</mn></msubsup><msup><mi>π</mi><mo>−</mo></msup><mo stretchy="false">)</mo><mo>=</mo><mspace linebreak="goodbreak"></mspace><mo stretchy="false">(</mo><mn>7.3</mn><mo>±</mo><mn>0.8</mn><mo>±</mo><mn>0.6</mn><mo stretchy="false">)</mo><mo>×</mo><msup><mn>10</mn><mrow><mo>−</mo><mn>4</mn></mrow></msup></math>. Here the uncertainties are statistical and systematic, respectively, and <math xmlns="http://www.w3.org/1998/Math/MathML" display="inline"><msub><mi>f</mi><msubsup><mi mathvariant="normal">Ξ</mi><mi>b</mi><mo>−</mo></msubsup></msub><mo stretchy="false">(</mo><msub><mi>f</mi><msubsup><mi mathvariant="normal">Λ</mi><mi>b</mi><mn>0</mn></msubsup></msub><mo stretchy="false">)</mo></math> is the fragmentation fraction for a <math xmlns="http://www.w3.org/1998/Math/MathML" display="inline"><mi>b</mi></math> quark into a <math xmlns="http://www.w3.org/1998/Math/MathML" display="inline"><msubsup><mi mathvariant="normal">Ξ</mi><mi>b</mi><mo>−</mo></msubsup></math> (<math xmlns="http://www.w3.org/1998/Math/MathML" display="inline"><msubsup><mi mathvariant="normal">Λ</mi><mi>b</mi><mn>0</mn></msubsup></math>) baryon. Using an independent measurement of <math xmlns="http://www.w3.org/1998/Math/MathML" display="inline"><msub><mi>f</mi><msubsup><mi mathvariant="normal">Ξ</mi><mi>b</mi><mo>−</mo></msubsup></msub><mo stretchy="false">/</mo><msub><mi>f</mi><msubsup><mi mathvariant="normal">Λ</mi><mi>b</mi><mn>0</mn></msubsup></msub></math>, the branching fraction <math xmlns="http://www.w3.org/1998/Math/MathML" display="inline"><mi mathvariant="script">B</mi><mo stretchy="false">(</mo><msubsup><mi mathvariant="normal">Ξ</mi><mi>b</mi><mo>−</mo></msubsup><mo stretchy="false">→</mo><msubsup><mi mathvariant="normal">Λ</mi><mi>b</mi><mn>0</mn></msubsup><msup><mi>π</mi><mo>−</mo></msup><mo stretchy="false">)</mo><mo>=</mo><mo stretchy="false">(</mo><mn>0.89</mn><mo>±</mo><mn>0.10</mn><mo>±</mo><mn>0.07</mn><mo>±</mo><mn>0.29</mn><mo stretchy="false">)</mo><mo>%</mo></math> is obtained, where the last uncertainty is due to the assumed SU(3) flavor symmetry in the determination of <math xmlns="http://www.w3.org/1998/Math/MathML" display="inline"><msub><mi>f</mi><msubsup><mi mathvariant="normal">Ξ</mi><mi>b</mi><mo>−</mo></msubsup></msub><mo stretchy="false">/</mo><msub><mi>f</mi><msubsup><mi mathvariant="normal">Λ</mi><mi>b</mi><mn>0</mn></msubsup></msub></math>.</p>',
    "title": 'Observation and branching fraction measurement of the decay <math xmlns="http://www.w3.org/1998/Math/MathML" display="inline"><msubsup><mi mathvariant="normal">Ξ</mi><mi>b</mi><mo>−</mo></msubsup><mo stretchy="false">→</mo><msubsup><mi mathvariant="normal">Λ</mi><mi>b</mi><mn>0</mn></msubsup><msup><mi>π</mi><mo>−</mo></msup></math>',
    "authors": [
        {
            "full_name": "Jaimes Elles, S.J.",
            "given_names": "S.J.",
            "surname": "Jaimes Elles",
            "affiliations": [
                {
                    "value": "Instituto de Fisica Corpuscular, Centro Mixto Universidad de Valencia—CSIC, Valencia, Spain",
                    "organization": "Instituto de Fisica Corpuscular, Centro Mixto Universidad de Valencia—CSIC, Valencia",
                },
                {
                    "value": "Departamento de Fisica, Universidad Nacional de Colombia, Bogota, Colombia (associated with LPNHE, Sorbonne Université, Paris Diderot Sorbonne Paris Cité, CNRS/IN2P3, Paris, France)",
                    "organization": "Departamento de Fisica, Universidad Nacional de Colombia, Bogota, Colombia (associated with LPNHE, Sorbonne Université, Paris Diderot Sorbonne Paris Cité, CNRS/IN2P3, Paris",
                },
            ],
        },
        {
            "full_name": "Jakobsen, S.",
            "given_names": "S.",
            "surname": "Jakobsen",
            "affiliations": [
                {
                    "value": "European Organization for Nuclear Research (CERN), Geneva, Switzerland",
                    "organization": "European Organization for Nuclear Research (CERN), Geneva",
                }
            ],
        },
        {
            "full_name": "Jashal, B.K.",
            "given_names": "B.K.",
            "surname": "Jashal",
            "affiliations": [
                {
                    "value": "Instituto de Fisica Corpuscular, Centro Mixto Universidad de Valencia—CSIC, Valencia, Spain",
                    "organization": "Instituto de Fisica Corpuscular, Centro Mixto Universidad de Valencia—CSIC, Valencia",
                }
            ],
        },
        {
            "full_name": "Jawahery, A.",
            "given_names": "A.",
            "surname": "Jawahery",
            "affiliations": [
                {
                    "value": "University of Maryland, College Park, Maryland, USA",
                    "organization": "University of Maryland, College Park, Maryland",
                }
            ],
        },
        {
            "full_name": "Jevtic, V.",
            "given_names": "V.",
            "surname": "Jevtic",
            "affiliations": [
                {
                    "value": "Fakultät Physik, Technische Universität Dortmund, Dortmund, Germany",
                    "organization": "Fakultät Physik, Technische Universität Dortmund, Dortmund",
                }
            ],
        },
        {
            "full_name": "Kulikova, E.",
            "given_names": "E.",
            "surname": "Kulikova",
            "affiliations": [
                {
                    "value": "Affiliated with an institute covered by a cooperation agreement with CERN"
                }
            ],
        },
        {
            "full_name": "Kutsenko, B.K.",
            "given_names": "B.K.",
            "surname": "Kutsenko",
            "affiliations": [
                {
                    "value": "Aix Marseille Université, CNRS/IN2P3, CPPM, Marseille, France",
                    "organization": "Aix Marseille Université, CNRS/IN2P3, CPPM, Marseille",
                }
            ],
        },
    ],
    "date_published": "2023-10-06",
    "copyright_holder": "CERN",
    "copyright_year": 2023,
    "copyright_statement": "© 2023 CERN, for the LHCb Collaboration",
    "license": [
        {"url": "https://creativecommons.org/licenses/by/4.0/", "license": "CC-BY-4.0"}
    ],
    "collections": [
        {"primary": "HEP"},
        {"primary": "Citeable"},
        {"primary": "Published"},
    ],
    "publication_info": [
        {
            "journal_title": "Physical Review D",
            "journal_volume": "108",
            "year": 2023,
            "journal_issue": "7",
            "material": "article",
        }
    ],
}

expected_wrong_author_affiliation_2 = {
    "dois": [{"value": "10.1103/PhysRevD.108.072002"}],
    "page_nr": [16],
    "arxiv_eprints": [{"value": "2307.09427"}],
    "abstracts": [
        {
            "source": "Springer",
            "value": '<p>The decay <math xmlns="http://www.w3.org/1998/Math/MathML" display="inline"><msubsup><mi mathvariant="normal">Ξ</mi><mi>b</mi><mo>−</mo></msubsup><mo stretchy="false">→</mo><msubsup><mi mathvariant="normal">Λ</mi><mi>b</mi><mn>0</mn></msubsup><msup><mi>π</mi><mo>−</mo></msup></math> is observed using a proton-proton collision data sample collected at center-of-mass energy <math xmlns="http://www.w3.org/1998/Math/MathML" display="inline"><msqrt><mi>s</mi></msqrt><mo>=</mo><mn>13</mn><mtext> </mtext><mtext> </mtext><mi>TeV</mi></math> with the LHCb detector, corresponding to an integrated luminosity of <math xmlns="http://www.w3.org/1998/Math/MathML" display="inline"><mn>5.5</mn><mtext> </mtext><mtext> </mtext><msup><mi>fb</mi><mrow><mo>−</mo><mn>1</mn></mrow></msup></math>. This process is mediated by the <math xmlns="http://www.w3.org/1998/Math/MathML" display="inline"><mi>s</mi><mo stretchy="false">→</mo><mi>u</mi><mover accent="true"><mi>u</mi><mo stretchy="false">¯</mo></mover><mi>d</mi></math> quark-level transition, where the <math xmlns="http://www.w3.org/1998/Math/MathML" display="inline"><mi>b</mi></math> quark in the <math xmlns="http://www.w3.org/1998/Math/MathML" display="inline"><msubsup><mi mathvariant="normal">Ξ</mi><mi>b</mi><mo>−</mo></msubsup></math> baryon is a spectator in the decay. Averaging the results obtained using the two <math xmlns="http://www.w3.org/1998/Math/MathML" display="inline"><msubsup><mi mathvariant="normal">Λ</mi><mi>b</mi><mn>0</mn></msubsup></math> decay modes, <math xmlns="http://www.w3.org/1998/Math/MathML" display="inline"><msubsup><mi mathvariant="normal">Λ</mi><mi>b</mi><mn>0</mn></msubsup><mo stretchy="false">→</mo><msubsup><mi mathvariant="normal">Λ</mi><mi>c</mi><mo>+</mo></msubsup><msup><mi>π</mi><mo>−</mo></msup></math> and <math xmlns="http://www.w3.org/1998/Math/MathML" display="inline"><msubsup><mi mathvariant="normal">Λ</mi><mi>b</mi><mn>0</mn></msubsup><mo stretchy="false">→</mo><msubsup><mi mathvariant="normal">Λ</mi><mi>c</mi><mo>+</mo></msubsup><msup><mi>π</mi><mo>−</mo></msup><msup><mi>π</mi><mo>+</mo></msup><msup><mi>π</mi><mo>−</mo></msup></math>, the relative production ratio is measured to be <math xmlns="http://www.w3.org/1998/Math/MathML" display="inline"><mo stretchy="false">(</mo><msub><mi>f</mi><msubsup><mi mathvariant="normal">Ξ</mi><mi>b</mi><mo>−</mo></msubsup></msub><mo stretchy="false">/</mo><msub><mi>f</mi><msubsup><mi mathvariant="normal">Λ</mi><mi>b</mi><mn>0</mn></msubsup></msub><mo stretchy="false">)</mo><mi mathvariant="script">B</mi><mo stretchy="false">(</mo><msubsup><mi mathvariant="normal">Ξ</mi><mi>b</mi><mo>−</mo></msubsup><mo stretchy="false">→</mo><msubsup><mi mathvariant="normal">Λ</mi><mi>b</mi><mn>0</mn></msubsup><msup><mi>π</mi><mo>−</mo></msup><mo stretchy="false">)</mo><mo>=</mo><mspace linebreak="goodbreak"></mspace><mo stretchy="false">(</mo><mn>7.3</mn><mo>±</mo><mn>0.8</mn><mo>±</mo><mn>0.6</mn><mo stretchy="false">)</mo><mo>×</mo><msup><mn>10</mn><mrow><mo>−</mo><mn>4</mn></mrow></msup></math>. Here the uncertainties are statistical and systematic, respectively, and <math xmlns="http://www.w3.org/1998/Math/MathML" display="inline"><msub><mi>f</mi><msubsup><mi mathvariant="normal">Ξ</mi><mi>b</mi><mo>−</mo></msubsup></msub><mo stretchy="false">(</mo><msub><mi>f</mi><msubsup><mi mathvariant="normal">Λ</mi><mi>b</mi><mn>0</mn></msubsup></msub><mo stretchy="false">)</mo></math> is the fragmentation fraction for a <math xmlns="http://www.w3.org/1998/Math/MathML" display="inline"><mi>b</mi></math> quark into a <math xmlns="http://www.w3.org/1998/Math/MathML" display="inline"><msubsup><mi mathvariant="normal">Ξ</mi><mi>b</mi><mo>−</mo></msubsup></math> (<math xmlns="http://www.w3.org/1998/Math/MathML" display="inline"><msubsup><mi mathvariant="normal">Λ</mi><mi>b</mi><mn>0</mn></msubsup></math>) baryon. Using an independent measurement of <math xmlns="http://www.w3.org/1998/Math/MathML" display="inline"><msub><mi>f</mi><msubsup><mi mathvariant="normal">Ξ</mi><mi>b</mi><mo>−</mo></msubsup></msub><mo stretchy="false">/</mo><msub><mi>f</mi><msubsup><mi mathvariant="normal">Λ</mi><mi>b</mi><mn>0</mn></msubsup></msub></math>, the branching fraction <math xmlns="http://www.w3.org/1998/Math/MathML" display="inline"><mi mathvariant="script">B</mi><mo stretchy="false">(</mo><msubsup><mi mathvariant="normal">Ξ</mi><mi>b</mi><mo>−</mo></msubsup><mo stretchy="false">→</mo><msubsup><mi mathvariant="normal">Λ</mi><mi>b</mi><mn>0</mn></msubsup><msup><mi>π</mi><mo>−</mo></msup><mo stretchy="false">)</mo><mo>=</mo><mo stretchy="false">(</mo><mn>0.89</mn><mo>±</mo><mn>0.10</mn><mo>±</mo><mn>0.07</mn><mo>±</mo><mn>0.29</mn><mo stretchy="false">)</mo><mo>%</mo></math> is obtained, where the last uncertainty is due to the assumed SU(3) flavor symmetry in the determination of <math xmlns="http://www.w3.org/1998/Math/MathML" display="inline"><msub><mi>f</mi><msubsup><mi mathvariant="normal">Ξ</mi><mi>b</mi><mo>−</mo></msubsup></msub><mo stretchy="false">/</mo><msub><mi>f</mi><msubsup><mi mathvariant="normal">Λ</mi><mi>b</mi><mn>0</mn></msubsup></msub></math>.</p>',
        }
    ],
    "titles": [
        {
            "source": "Springer",
            "subtitle": "",
            "title": 'Observation and branching fraction measurement of the decay <math xmlns="http://www.w3.org/1998/Math/MathML" display="inline"><msubsup><mi mathvariant="normal">Ξ</mi><mi>b</mi><mo>−</mo></msubsup><mo stretchy="false">→</mo><msubsup><mi mathvariant="normal">Λ</mi><mi>b</mi><mn>0</mn></msubsup><msup><mi>π</mi><mo>−</mo></msup></math>',
        }
    ],
    "authors": [
        {
            "full_name": "Jaimes Elles, S.J.",
            "given_names": "S.J.",
            "surname": "Jaimes Elles",
            "affiliations": [
                {
                    "value": "Instituto de Fisica Corpuscular, Centro Mixto Universidad de Valencia—CSIC, Valencia, Spain",
                    "organization": "Instituto de Fisica Corpuscular, Centro Mixto Universidad de Valencia—CSIC, Valencia",
                    "country": "Spain",
                },
                {
                    "value": "Departamento de Fisica, Universidad Nacional de Colombia, Bogota, Colombia (associated with LPNHE, Sorbonne Université, Paris Diderot Sorbonne Paris Cité, CNRS/IN2P3, Paris, France)",
                    "organization": "Departamento de Fisica, Universidad Nacional de Colombia, Bogota, Colombia (associated with LPNHE, Sorbonne Université, Paris Diderot Sorbonne Paris Cité, CNRS/IN2P3, Paris",
                    "country": "France",
                },
            ],
        },
        {
            "full_name": "Jakobsen, S.",
            "given_names": "S.",
            "surname": "Jakobsen",
            "affiliations": [
                {
                    "value": "European Organization for Nuclear Research (CERN), Geneva, Switzerland",
                    "organization": "European Organization for Nuclear Research (CERN), Geneva",
                    "country": "CERN",
                }
            ],
        },
        {
            "full_name": "Jashal, B.K.",
            "given_names": "B.K.",
            "surname": "Jashal",
            "affiliations": [
                {
                    "value": "Instituto de Fisica Corpuscular, Centro Mixto Universidad de Valencia—CSIC, Valencia, Spain",
                    "organization": "Instituto de Fisica Corpuscular, Centro Mixto Universidad de Valencia—CSIC, Valencia",
                    "country": "Spain",
                }
            ],
        },
        {
            "full_name": "Jawahery, A.",
            "given_names": "A.",
            "surname": "Jawahery",
            "affiliations": [
                {
                    "value": "University of Maryland, College Park, Maryland, USA",
                    "organization": "University of Maryland, College Park, Maryland",
                    "country": "USA",
                }
            ],
        },
        {
            "full_name": "Jevtic, V.",
            "given_names": "V.",
            "surname": "Jevtic",
            "affiliations": [
                {
                    "value": "Fakultät Physik, Technische Universität Dortmund, Dortmund, Germany",
                    "organization": "Fakultät Physik, Technische Universität Dortmund, Dortmund",
                    "country": "Germany",
                }
            ],
        },
        {
            "full_name": "Kulikova, E.",
            "given_names": "E.",
            "surname": "Kulikova",
            "affiliations": [
                {
                    "value": "Affiliated with an institute covered by a cooperation agreement with CERN",
                }
            ],
        },
        {
            "full_name": "Kutsenko, B.K.",
            "given_names": "B.K.",
            "surname": "Kutsenko",
            "affiliations": [
                {
                    "value": "Aix Marseille Université, CNRS/IN2P3, CPPM, Marseille, France",
                    "organization": "Aix Marseille Université, CNRS/IN2P3, CPPM, Marseille",
                    "country": "France",
                }
            ],
        },
    ],
    "imprints": [{"date": "2023-10-06", "publisher": "Springer"}],
    "copyright": [
        {
            "holder": "CERN",
            "material": "",
            "year": 2023,
            "statement": "© 2023 CERN, for the LHCb Collaboration",
        }
    ],
    "license": [
        {"url": "https://creativecommons.org/licenses/by/4.0/", "license": "CC-BY-4.0"}
    ],
    "collections": [
        {"primary": "HEP"},
        {"primary": "Citeable"},
        {"primary": "Published"},
    ],
    "publication_info": [
        {
            "journal_title": "Physical Review D",
            "journal_volume": "108",
            "year": 2023,
            "journal_issue": "7",
            "material": "article",
        },
    ],
    "acquisition_source": {
        "date": "2022-05-20T00:00:00",
        "method": "Springer",
        "source": "Springer",
    },
    "record_creation_date": "2022-05-20T00:00:00",
}


@pytest.mark.parametrize(
    "test_input, expected, publisher",
    [
        pytest.param(generic_pseudo_parser_output, expected_output, publisher),
        pytest.param(
            empty_generic_pseudo_parser_output,
            expected_output_from_empty_input,
            publisher,
        ),
        pytest.param(
            input_with_affiliation_of_cooperation_agreement_with_CERN,
            expected_output_with_affiliation_of_cooperation_agreement_with_CERN,
            publisher,
        ),
        pytest.param(
            input_with_correct_affiliation, output_with_correct_affiliation, publisher
        ),
        pytest.param(
            input_with_affiliation_of_cooperation_agreement_with_CERN_no_country,
            expected_output_with_affiliation_of_cooperation_agreement_with_CERN,
            publisher,
        ),
        pytest.param(
            input_with_affiliation_value_only,
            expected_output_with_affiliation_value_only,
            publisher,
        ),
        pytest.param(
            wrong_author_affiliation_2,
            expected_wrong_author_affiliation_2,
            publisher,
        ),
    ],
)
@freeze_time("2022-05-20")
def test_all_contructors(test_input, expected, publisher):
    enhancement = Enhancer()
    enhanced = enhancement(item=test_input, publisher=publisher)
    assert enhanced == expected


@pytest.mark.skip
@pytest.mark.parametrize(
    "test_input, expected, publisher",
    [
        pytest.param(
            wrong_author_affiliation,
            expected_wrong_author_affiliation,
            publisher,
        ),
    ],
)
@freeze_time("2022-05-20")
def test_all_contructors_failing_with_wrong_affiliation_value(
    test_input, expected, publisher
):
    enhancement = Enhancer()
    enhanced = enhancement(item=test_input, publisher=publisher)
    assert enhanced == expected
