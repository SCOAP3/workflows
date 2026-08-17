import base64
from io import BytesIO
from unittest import mock

import pytest
from airflow.models import DagBag


class _S3Object:
    def __init__(self, key):
        self.key = key


def _springer_xml_with_doi(doi):
    return f"""<?xml version=\"1.0\" encoding=\"UTF-8\"?>
<Publisher>
  <Journal>
    <Volume>
      <Issue>
        <Article>
          <ArticleInfo>
            <ArticleDOI>{doi}</ArticleDOI>
          </ArticleInfo>
        </Article>
      </Issue>
    </Volume>
  </Journal>
</Publisher>
""".encode()


@pytest.fixture(scope="class")
def dagbag():
    return DagBag(dag_folder="dags/", include_examples=False)


@pytest.mark.usefixtures("dagbag")
class TestUnitSpringerReharvest:
    def setup_method(self):
        self.dag_id = "springer_reharvest"
        dagbag = DagBag(dag_folder="dags/", include_examples=False)
        self.dag = dagbag.dags.get(self.dag_id)
        assert self.dag is not None, f"DAG {self.dag_id} failed to load"

    def _build_repo(self, payload_by_key):
        mock_repo = mock.MagicMock()
        mock_repo.EXTRACTED_DIR = "extracted/"
        mock_repo.s3.objects.filter.return_value.all.return_value = [
            _S3Object(key) for key in payload_by_key
        ]
        mock_repo.is_meta.side_effect = lambda key: key.endswith(
            ".Meta"
        ) or key.endswith(".scoap")

        def _get_by_id(key):
            return BytesIO(payload_by_key[key])

        mock_repo.get_by_id.side_effect = _get_by_id
        return mock_repo

    def test_dag_structure(self):
        assert "springer_reharvest_trigger_file_processing" in self.dag.task_ids
        task = self.dag.get_task("springer_reharvest_trigger_file_processing")
        assert "MappedOperator" in str(type(task)) or task.is_mapped
        assert task.partial_kwargs["trigger_dag_id"] == "springer_process_file"
        assert task.partial_kwargs["reset_dag_run"] is True

    def test_collect_records_file_keys_and_dois_filters_resolved_keys(self):
        task = self.dag.get_task("collect_records")
        function_to_unit_test = task.python_callable

        payload_by_key = {
            "extracted/EPJC/ftp_PUB_25-03-01_00-00-00/article.Meta": _springer_xml_with_doi(
                "10.1007/one"
            ),
            "extracted/EPJC/ftp_PUB_26-03-29_20-00-46/article.Meta": _springer_xml_with_doi(
                "10.1007/one"
            ),
            "extracted/JHEP/ftp_PUB_26-03-30_20-00-50/other.Meta": _springer_xml_with_doi(
                "10.1007/two"
            ),
        }
        mock_repo = self._build_repo(payload_by_key)

        result = function_to_unit_test(
            repo=mock_repo,
            params={
                "file_keys": ["*"],
                "dois": ["10.1007/one"],
            },
        )

        assert result == ["extracted/EPJC/ftp_PUB_26-03-29_20-00-46/article.Meta"]

    def test_collect_records_date_range_dedup_keeps_newest(self):
        task = self.dag.get_task("collect_records")
        function_to_unit_test = task.python_callable

        payload_by_key = {
            "extracted/EPJC/ftp_PUB_25-08-15_00-00-00/article.Meta": _springer_xml_with_doi(
                "10.1007/one"
            ),
            "extracted/JHEP/ftp_PUB_26-01-30_20-00-50/article.Meta": _springer_xml_with_doi(
                "10.1007/one"
            ),
            "extracted/JHEP/ftp_PUB_25-12-19_20-00-50/other.scoap": _springer_xml_with_doi(
                "10.1007/two"
            ),
            "extracted/JHEP/not-a-drop/ignored.Meta": _springer_xml_with_doi(
                "10.1007/three"
            ),
        }
        mock_repo = self._build_repo(payload_by_key)

        result = function_to_unit_test(
            repo=mock_repo,
            params={
                "date_from": "2025-08-15",
                "date_to": "2026-01-30",
            },
        )

        assert len(result) == 2
        assert "extracted/JHEP/ftp_PUB_26-01-30_20-00-50/article.Meta" in result
        assert "extracted/JHEP/ftp_PUB_25-12-19_20-00-50/other.scoap" in result

    def test_collect_records_glob_patterns(self):
        task = self.dag.get_task("collect_records")
        function_to_unit_test = task.python_callable

        payload_by_key = {
            "extracted/EPJC/ftp_PUB_26-03-29_20-00-46/article.Meta": _springer_xml_with_doi(
                "10.1007/one"
            ),
            "extracted/JHEP/ftp_PUB_26-03-30_20-00-50/other.scoap": _springer_xml_with_doi(
                "10.1007/two"
            ),
        }
        mock_repo = self._build_repo(payload_by_key)

        result_all = function_to_unit_test(
            repo=mock_repo,
            params={"file_keys": ["*"]},
        )
        assert set(result_all) == set(payload_by_key.keys())

        result_epjc = function_to_unit_test(
            repo=mock_repo,
            params={"file_keys": ["EPJC/*"]},
        )
        assert result_epjc == ["extracted/EPJC/ftp_PUB_26-03-29_20-00-46/article.Meta"]

    def test_collect_records_limit_exceeded_raises(self):
        task = self.dag.get_task("collect_records")
        function_to_unit_test = task.python_callable

        payload_by_key = {
            "extracted/EPJC/ftp_PUB_26-03-29_20-00-46/article.Meta": _springer_xml_with_doi(
                "10.1007/one"
            ),
            "extracted/JHEP/ftp_PUB_26-03-30_20-00-50/other.scoap": _springer_xml_with_doi(
                "10.1007/two"
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

    def test_prepare_trigger_conf_dry_run_and_normal(self):
        task = self.dag.get_task("prepare_trigger_conf")
        function_to_unit_test = task.python_callable

        file_key = "extracted/EPJC/ftp_PUB_26-03-29_20-00-46/article.Meta"
        xml_bytes = _springer_xml_with_doi("10.1007/one")

        mock_repo = mock.MagicMock()
        mock_repo.get_by_id.return_value = BytesIO(xml_bytes)

        dry_run_result = function_to_unit_test(
            file_keys=[file_key],
            repo=mock_repo,
            params={"dry_run": True},
        )
        assert dry_run_result == []

        normal_result = function_to_unit_test(
            file_keys=[file_key],
            repo=mock_repo,
            params={"dry_run": False},
        )
        assert len(normal_result) == 1
        assert normal_result[0]["file_name"] == file_key

        decoded_xml = base64.b64decode(normal_result[0]["file"]).decode("utf-8")
        assert "10.1007/one" in decoded_xml
