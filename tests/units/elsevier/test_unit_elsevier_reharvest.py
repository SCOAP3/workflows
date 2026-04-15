from datetime import date
from io import BytesIO
from unittest import mock

import pytest
from airflow.models import DagBag


class _S3Object:
    def __init__(self, key):
        self.key = key


def _main_xml_with_doi_and_received_date(doi, year, month, day):
    return f'''<?xml version="1.0" encoding="UTF-8"?>
<article xmlns="http://www.elsevier.com/xml/ja/dtd"
    xmlns:ce="http://www.elsevier.com/xml/common/dtd">
  <item-info>
    <ce:doi>{doi}</ce:doi>
  </item-info>
  <head>
    <ce:date-received day="{day}" month="{month}" year="{year}"/>
  </head>
</article>
'''.encode()


def _dataset_xml():
    return b"<dataset><dataset-content></dataset-content></dataset>"


@pytest.fixture(scope="class")
def dagbag():
    return DagBag(dag_folder="dags/", include_examples=False)


@pytest.mark.usefixtures("dagbag")
class TestUnitElsevierReharvest:
    def setup_method(self):
        self.dag_id = "elsevier_reharvest"
        dagbag = DagBag(dag_folder="dags/", include_examples=False)
        self.dag = dagbag.dags.get(self.dag_id)
        assert self.dag is not None, f"DAG {self.dag_id} failed to load"

    def _build_repo(self, payload_by_key):
        mock_repo = mock.MagicMock()
        mock_repo.EXTRACTED_DIR = "extracted/"
        mock_repo.s3.objects.filter.return_value.all.return_value = [
            _S3Object(key) for key in payload_by_key
        ]

        def _get_by_id(key):
            return BytesIO(payload_by_key[key])

        mock_repo.get_by_id.side_effect = _get_by_id
        return mock_repo

    def test_dag_structure(self):
        assert "elsevier_reharvest_trigger_file_processing" in self.dag.task_ids
        task = self.dag.get_task("elsevier_reharvest_trigger_file_processing")
        assert "MappedOperator" in str(type(task)) or task.is_mapped
        assert task.partial_kwargs["trigger_dag_id"] == "elsevier_process_file"
        assert task.partial_kwargs["reset_dag_run"] is True

    def test_collect_records_file_keys_and_dois_filters_resolved_keys(self):
        task = self.dag.get_task("collect_records")
        function_to_unit_test = task.python_callable

        payload_by_key = {
            "extracted/CERNAB00000010772A/CERNAB00000010772/older/article/main.xml": _main_xml_with_doi_and_received_date(
                "10.1016/one", 2025, 1, 10
            ),
            "extracted/CERNAB00000010772A/CERNAB00000010772/newer/article/main.xml": _main_xml_with_doi_and_received_date(
                "10.1016/one", 2025, 2, 10
            ),
            "extracted/CERNAB00000010772A/CERNAB00000010772/other/article/main.xml": _main_xml_with_doi_and_received_date(
                "10.1016/two", 2025, 3, 10
            ),
        }
        mock_repo = self._build_repo(payload_by_key)

        result = function_to_unit_test(
            repo=mock_repo,
            params={
                "file_keys": ["*"],
                "dois": ["10.1016/one"],
            },
        )

        assert result == [
            "extracted/CERNAB00000010772A/CERNAB00000010772/newer/article/main.xml"
        ]

    def test_collect_records_date_range_uses_received_date_from_xml(self):
        task = self.dag.get_task("collect_records")
        function_to_unit_test = task.python_callable

        payload_by_key = {
            "extracted/CERNAB00000010772A/CERNAB00000010772/in-range/main.xml": _main_xml_with_doi_and_received_date(
                "10.1016/one", 2025, 9, 5
            ),
            "extracted/CERNAB00000010772A/CERNAB00000010772/out-of-range/main.xml": _main_xml_with_doi_and_received_date(
                "10.1016/two", 2025, 6, 1
            ),
        }
        mock_repo = self._build_repo(payload_by_key)

        result = function_to_unit_test(
            repo=mock_repo,
            params={
                "date_from": "2025-09-01",
                "date_to": "2025-09-30",
            },
        )

        assert result == [
            "extracted/CERNAB00000010772A/CERNAB00000010772/in-range/main.xml"
        ]

    def test_collect_records_limit_exceeded_raises(self):
        task = self.dag.get_task("collect_records")
        function_to_unit_test = task.python_callable

        payload_by_key = {
            "extracted/CERNAB00000010772A/CERNAB00000010772/one/main.xml": _main_xml_with_doi_and_received_date(
                "10.1016/one", 2025, 7, 1
            ),
            "extracted/CERNAB00000010772A/CERNAB00000010772/two/main.xml": _main_xml_with_doi_and_received_date(
                "10.1016/two", 2025, 7, 2
            ),
        }
        mock_repo = self._build_repo(payload_by_key)

        with pytest.raises(ValueError, match="above limit"):
            function_to_unit_test(
                repo=mock_repo,
                params={
                    "file_keys": ["*"],
                    "limit": 1,
                },
            )

    def test_collect_records_logs_and_raises_when_date_scan_is_over_10k(self):
        task = self.dag.get_task("collect_records")
        function_to_unit_test = task.python_callable

        mock_repo = mock.MagicMock()
        mock_repo.EXTRACTED_DIR = "extracted/"
        mock_repo.s3.objects.filter.return_value.all.return_value = [
            _S3Object(f"extracted/collection/{i}/main.xml") for i in range(10001)
        ]
        mock_repo.get_by_id.return_value = BytesIO(b"<article/>")

        mocked_logger = mock.MagicMock()
        with (
            mock.patch.dict(
                function_to_unit_test.__globals__,
                {
                    "logger": mocked_logger,
                    "_extract_received_date_from_xml": lambda _: date(2025, 9, 5),
                },
            ),
            pytest.raises(ValueError, match="XML scan threshold exceeded"),
        ):
            function_to_unit_test(
                repo=mock_repo,
                params={
                    "date_from": "2025-09-01",
                    "date_to": "2025-09-30",
                },
            )

        mocked_logger.error.assert_any_call(
            "XML scan threshold exceeded for %s: %s files to parse (> %s). "
            "Consider narrowing filters.",
            "ce:date-received extraction from all main.xml candidates",
            10001,
            10000,
        )

    def test_collect_records_logs_and_raises_when_file_keys_doi_scan_is_over_10k(self):
        task = self.dag.get_task("collect_records")
        function_to_unit_test = task.python_callable

        mock_repo = mock.MagicMock()
        mock_repo.EXTRACTED_DIR = "extracted/"
        mock_repo.s3.objects.filter.return_value.all.return_value = [
            _S3Object(f"extracted/collection/{i}/main.xml") for i in range(10001)
        ]
        mock_repo.get_by_id.return_value = BytesIO(b"<article/>")

        mocked_logger = mock.MagicMock()
        with (
            mock.patch.dict(
                function_to_unit_test.__globals__,
                {
                    "logger": mocked_logger,
                    "_extract_received_date_from_xml": lambda _: date(2025, 9, 5),
                    "_extract_doi_from_xml": lambda _: "10.1016/one",
                },
            ),
            pytest.raises(ValueError, match="XML scan threshold exceeded"),
        ):
            function_to_unit_test(
                repo=mock_repo,
                params={
                    "file_keys": ["*"],
                    "dois": ["10.1016/one"],
                },
            )

        mocked_logger.error.assert_any_call(
            "XML scan threshold exceeded for %s: %s files to parse (> %s). "
            "Consider narrowing filters.",
            "date extraction for sorting file_keys before DOI filtering",
            10001,
            10000,
        )

    def test_prepare_trigger_conf_dry_run_and_normal(self):
        task = self.dag.get_task("prepare_trigger_conf")
        function_to_unit_test = task.python_callable

        file_key = (
            "extracted/CERNAB00000010772A/"
            "CERNAB00000010772/03702693/v846sC/S0370269322005871/main.xml"
        )
        dataset_key = "extracted/CERNAB00000010772A/CERNAB00000010772/dataset.xml"

        mock_repo = mock.MagicMock()
        mock_repo.EXTRACTED_DIR = "extracted/"
        mock_repo.s3.objects.filter.return_value.all.return_value = [
            _S3Object(file_key),
            _S3Object(dataset_key),
        ]
        mock_repo.get_by_id.return_value = BytesIO(_dataset_xml())

        dry_run_result = function_to_unit_test(
            file_keys=[file_key],
            repo=mock_repo,
            params={"dry_run": True},
        )
        assert dry_run_result == []

        mocked_trigger = mock.MagicMock(
            return_value=[
                {
                    "file_name": file_key,
                    "metadata": {"files": {"xml": file_key}, "meta": "data1"},
                }
            ]
        )

        with mock.patch.dict(
            function_to_unit_test.__globals__,
            {"trigger_file_processing_elsevier": mocked_trigger},
        ):
            normal_result = function_to_unit_test(
                file_keys=[file_key],
                repo=mock_repo,
                params={"dry_run": False},
            )

        assert normal_result == [
            {
                "file_name": file_key,
                "metadata": {"files": {"xml": file_key}, "meta": "data1"},
            }
        ]
