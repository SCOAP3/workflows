import json
from io import BytesIO
from unittest import mock

import pytest
from airflow.models import DagBag
from freezegun import freeze_time


class _S3Object:
    def __init__(self, key):
        self.key = key


@pytest.fixture(scope="class")
def dagbag():
    return DagBag(dag_folder="dags/", include_examples=False)


@pytest.fixture(scope="class")
def dag(dagbag):
    return dagbag.dags.get("jagiellonian_reharvest")


class TestUnitJagiellonianReharvest:
    def _build_repo(self, payload_by_key):
        mock_repo = mock.MagicMock()
        keys = list(payload_by_key.keys())
        mock_repo.s3_bucket.objects.all.return_value = [_S3Object(key) for key in keys]

        def _get_by_id(key):
            return BytesIO(json.dumps(payload_by_key[key]).encode("utf-8"))

        mock_repo.get_by_id.side_effect = _get_by_id
        return mock_repo

    def test_dag_structure(self, dag):
        assert "jagiellonian_reharvest_trigger_file_processing" in dag.task_ids
        task = dag.get_task("jagiellonian_reharvest_trigger_file_processing")
        assert "MappedOperator" in str(type(task)) or task.is_mapped
        assert task.partial_kwargs["trigger_dag_id"] == "jagiellonian_process_file"
        assert task.partial_kwargs["reset_dag_run"] is True

    def test_collect_records_invalid_combination_dates_with_file_keys(self, dag):
        task = dag.get_task("collect_records")
        function_to_unit_test = task.python_callable

        mock_repo = self._build_repo({})

        with pytest.raises(
            ValueError, match="date_from/date_to cannot be used together with file_keys"
        ):
            function_to_unit_test(
                repo=mock_repo,
                params={
                    "file_keys": ["10.5506/a_metadata_2026-04-09 00:35:13+00:00.json"],
                    "date_from": "2026-04-01",
                    "date_to": "2026-04-09",
                },
            )

    def test_collect_records_date_range_dedup_keeps_newest(self, dag):
        task = dag.get_task("collect_records")
        function_to_unit_test = task.python_callable

        payload_by_key = {
            "10.5506/aphyspolb.57.4-a4_metadata_2026-04-09 00_35_13.599324+00_00.json": {
                "dois": [{"value": "10.5506/aphyspolb.57.4-a4"}],
                "titles": [{"title": "new"}],
            },
            "10.5506/aphyspolb.57.4-a4_metadata_2026-04-09 00_10_13.599324+00_00.json": {
                "dois": [{"value": "10.5506/aphyspolb.57.4-a4"}],
                "titles": [{"title": "old"}],
            },
            "10.5506/aphyspolb.57.4-a5_metadata_2026-04-09 00_20_00.000000+00_00.json": {
                "dois": [{"value": "10.5506/aphyspolb.57.4-a5"}],
            },
        }
        mock_repo = self._build_repo(payload_by_key)

        result = function_to_unit_test(
            repo=mock_repo,
            params={"date_from": "2026-04-09", "date_to": "2026-04-09"},
        )

        assert len(result) == 2
        doi_to_title = {
            article["dois"][0]["value"]: (article.get("titles") or [{"title": None}])[
                0
            ]["title"]
            for article in result
        }
        assert doi_to_title["10.5506/aphyspolb.57.4-a4"] == "new"

    def test_collect_records_file_keys_glob_patterns(self, dag):
        task = dag.get_task("collect_records")
        function_to_unit_test = task.python_callable

        payload_by_key = {
            "10.5506/aphyspolb.57.4-a4_metadata_2026-04-09 00_35_13.599324+00_00.json": {
                "dois": [{"value": "10.5506/aphyspolb.57.4-a4"}],
            },
            "10.5506/aphyspolb.57.4-a5_metadata_2026-04-09 00_35_13.599324+00_00.json": {
                "dois": [{"value": "10.5506/aphyspolb.57.4-a5"}],
            },
            "10.5506/aphyspolb.57.4-a6_metadata_2026-04-10 00_35_13.599324+00_00.json": {
                "dois": [{"value": "10.5506/aphyspolb.57.4-a6"}],
            },
        }
        mock_repo = self._build_repo(payload_by_key)

        result = function_to_unit_test(
            repo=mock_repo,
            params={"file_keys": ["10.5506/*_metadata_2026-04-09*.json"]},
        )

        dois = sorted([article["dois"][0]["value"] for article in result])
        assert dois == ["10.5506/aphyspolb.57.4-a4", "10.5506/aphyspolb.57.4-a5"]

    @freeze_time("2026-04-20")
    def test_collect_records_dois_without_dates_defaults_last_3_years(self, dag):
        task = dag.get_task("collect_records")
        function_to_unit_test = task.python_callable

        payload_by_key = {
            "10.5506/old_metadata_2020-01-01 00_00_00.000000+00_00.json": {
                "dois": [{"value": "10.5506/old"}],
            },
            "10.5506/new_metadata_2026-04-09 00_35_13.599324+00_00.json": {
                "dois": [{"value": "10.5506/new"}],
            },
        }
        mock_repo = self._build_repo(payload_by_key)

        result = function_to_unit_test(
            repo=mock_repo,
            params={"dois": ["10.5506/new"]},
        )

        assert len(result) == 1
        assert result[0]["dois"][0]["value"] == "10.5506/new"

    def test_collect_records_limit_exceeded_raises(self, dag):
        task = dag.get_task("collect_records")
        function_to_unit_test = task.python_callable

        payload_by_key = {
            "10.5506/a_metadata_2026-04-09 00_00_00.000000+00_00.json": {
                "dois": [{"value": "10.5506/a"}],
            },
            "10.5506/b_metadata_2026-04-09 00_00_01.000000+00_00.json": {
                "dois": [{"value": "10.5506/b"}],
            },
        }
        mock_repo = self._build_repo(payload_by_key)

        with pytest.raises(ValueError, match="above limit"):
            function_to_unit_test(
                repo=mock_repo,
                params={
                    "date_from": "2026-04-09",
                    "date_to": "2026-04-09",
                    "limit": 1,
                },
            )

    def test_prepare_trigger_conf_dry_run_and_normal(self, dag):
        task = dag.get_task("prepare_trigger_conf")
        function_to_unit_test = task.python_callable

        records = [{"dois": [{"value": "10.5506/aphyspolb.57.4-a4"}]}]

        dry_run_result = function_to_unit_test(
            records=records, params={"dry_run": True}
        )
        assert dry_run_result == []

        normal_result = function_to_unit_test(
            records=records, params={"dry_run": False}
        )
        assert len(normal_result) == 1
        assert normal_result[0]["article"] == records[0]
