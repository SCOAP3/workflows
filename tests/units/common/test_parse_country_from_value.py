import json
from pathlib import Path

import pytest
from common.utils import parse_country_from_value


def load_test_data():
    json_path = Path(__file__).parent / "data/test_parse_country_from_value.json"
    with open(json_path, encoding="utf-8") as f:
        affiliations = json.load(f)

    test_cases = []
    ids = []
    for record in affiliations:
        test_cases.append(
            pytest.param(
                record["fields"]["value"],
                record["fields"]["country"],
                record["pk"],
            )
        )
        ids.append(f"pk={record['pk']}")

    return test_cases, ids


test_data_params, test_ids = load_test_data()


@pytest.mark.parametrize(
    "affiliation_str, iso_expected, pk",
    test_data_params,
    ids=test_ids,
)
def test_parse_country_codes(affiliation_str, iso_expected, pk):
    iso_parsed = parse_country_from_value(affiliation_str)
    assert iso_parsed == iso_expected, (
        f"pk={pk}: expected {iso_expected!r}, got {iso_parsed!r}\n"
        f" affiliation: {affiliation_str!r}"
    )
