import fnmatch
import logging
import os
from datetime import date, datetime, timedelta
from io import BytesIO

import pendulum
from airflow.providers.standard.operators.trigger_dagrun import TriggerDagRunOperator
from airflow.sdk import Param, dag, task
from common.notification_service import FailedDagNotifier
from common.utils import parse_without_names_spaces
from elsevier.repository import ElsevierRepository
from elsevier.trigger_file_processing import trigger_file_processing_elsevier

logger = logging.getLogger("airflow.task")
ELSEVIER_REPO = ElsevierRepository()
MAX_XML_SCAN_FILES = 10_000


def _parse_date(value):
    if not value:
        return None
    return datetime.strptime(value, "%Y-%m-%d").date()


def _normalize_dois(dois):
    if not dois:
        return set()
    return {doi.strip().lower() for doi in dois if isinstance(doi, str) and doi.strip()}


def _normalize_file_keys(file_keys):
    return [key.strip() for key in file_keys if isinstance(key, str) and key.strip()]


def _is_glob_pattern(value):
    return any(char in value for char in ("*", "?", "["))


def _is_elsevier_main_xml_key(key, repo):
    return key.startswith(repo.EXTRACTED_DIR) and os.path.basename(key) == "main.xml"


def _extract_doi_from_xml(xml_bytes):
    try:
        xml = parse_without_names_spaces(
            BytesIO(xml_bytes) if isinstance(xml_bytes, bytes) else xml_bytes
        )
        doi_element = xml.find("item-info/doi")
        if doi_element is not None and doi_element.text:
            return doi_element.text.strip().lower()
    except Exception:
        pass
    return None


def _extract_received_date_from_xml(xml_bytes):
    try:
        xml = parse_without_names_spaces(
            BytesIO(xml_bytes) if isinstance(xml_bytes, bytes) else xml_bytes
        )
        date_element = xml.find("head/date-received")
        if date_element is None:
            return None

        day_text = date_element.get("day")
        month_text = date_element.get("month")
        year_text = date_element.get("year")
        if not (day_text and month_text and year_text):
            return None

        return date(int(year_text), int(month_text), int(day_text))
    except Exception:
        return None


def _enforce_limit(records, limit):
    if limit is None:
        return
    if len(records) > limit:
        raise ValueError(
            f"Matched {len(records)} records, which is above limit={limit}. "
            "Please reduce the date range or increase the limit."
        )


def _log_if_xml_scan_exceeds_threshold(total_files, scan_reason):
    if total_files > MAX_XML_SCAN_FILES:
        logger.error(
            "XML scan threshold exceeded for %s: %s files to parse (> %s). "
            "Consider narrowing filters.",
            scan_reason,
            total_files,
            MAX_XML_SCAN_FILES,
        )
        raise ValueError(
            f"XML scan threshold exceeded for {scan_reason}: {total_files} files to parse (> {MAX_XML_SCAN_FILES}). Consider narrowing filters."
        )


def _resolve_file_keys(file_keys, all_xml_keys, repo):
    """Resolve a mix of exact S3 keys and glob patterns.

    Patterns are matched against the path after the leading repo.EXTRACTED_DIR prefix,
    so '*' matches every Elsevier main.xml key under that extracted folder.
    """
    all_xml_keys_set = set(all_xml_keys)
    prefix = repo.EXTRACTED_DIR

    exact_keys = [key for key in file_keys if not _is_glob_pattern(key)]
    glob_patterns = [key for key in file_keys if _is_glob_pattern(key)]

    missing = [key for key in exact_keys if key not in all_xml_keys_set]
    if missing:
        raise ValueError(f"Some requested file_keys do not exist: {missing}")

    resolved = list(exact_keys)

    for pattern in glob_patterns:
        matched = [
            key
            for key in all_xml_keys
            if fnmatch.fnmatch(
                key[len(prefix) :] if key.startswith(prefix) else key,
                pattern,
            )
        ]
        if not matched:
            logger.warning("Pattern %r matched no Elsevier main.xml keys", pattern)
        resolved.extend(matched)

    seen = set()
    deduped = []
    for key in resolved:
        if key not in seen:
            seen.add(key)
            deduped.append(key)
    return deduped


def _find_dataset_key_for_xml_key(xml_key, dataset_keys, repo):
    relative_key = (
        xml_key[len(repo.EXTRACTED_DIR) :]
        if xml_key.startswith(repo.EXTRACTED_DIR)
        else xml_key
    )
    parts = relative_key.split("/")

    for depth in range(len(parts) - 1, 0, -1):
        candidate = f"{repo.EXTRACTED_DIR}{'/'.join(parts[:depth])}/dataset.xml"
        if candidate in dataset_keys:
            return candidate

    return None


@dag(
    on_failure_callback=FailedDagNotifier(),
    start_date=pendulum.today("UTC").add(days=-1),
    schedule=None,
    catchup=False,
    tags=["reharvest", "elsevier"],
    params={
        "date_from": Param(
            default=None,
            type=["string", "null"],
            description="Start ce:date-received (from XML) in YYYY-MM-DD format",
            title="Date from",
        ),
        "date_to": Param(
            default=None,
            type=["string", "null"],
            description="End ce:date-received (from XML) in YYYY-MM-DD format",
            title="Date to",
        ),
        "file_keys": Param(
            default=[],
            type=["array", "null"],
            description=(
                "Exact Elsevier extracted main.xml keys or glob patterns matched relative "
                f"to '{ELSEVIER_REPO.EXTRACTED_DIR}'. Examples: '*' or "
                "'CERNAB00000010772A/*/*/*/main.xml'."
            ),
            title="File keys",
        ),
        "dois": Param(
            default=[],
            type=["array", "null"],
            description=(
                "List of DOIs to process. Can be used with date_from/date_to or together "
                "with file_keys to filter the resolved key set. The maximum date range is 1 Year."
            ),
            title="DOIs",
        ),
        "limit": Param(
            1000,
            type=["integer"],
            description="Maximum number of records to process",
            title="Limit",
        ),
        "dry_run": Param(
            default=True,
            type=["boolean", "null"],
            description="Whether to perform a dry run. If true, no downstream DAGs will be triggered",
            title="Dry run",
        ),
    },
)
def elsevier_reharvest():
    @task()
    def collect_records(repo=ELSEVIER_REPO, **kwargs):
        params = kwargs.get("params", {})

        date_from = _parse_date(params.get("date_from"))
        date_to = _parse_date(params.get("date_to"))
        file_keys = _normalize_file_keys(params.get("file_keys") or [])
        target_dois = _normalize_dois(params.get("dois") or [])
        limit = params.get("limit")

        if limit is not None and (not isinstance(limit, int) or limit <= 0):
            raise ValueError("limit must be a positive integer when provided")

        if bool(file_keys) and (date_from or date_to):
            raise ValueError(
                "Invalid parameters: date_from/date_to cannot be used together with file_keys"
            )

        if (date_from and not date_to) or (date_to and not date_from):
            raise ValueError("Both date_from and date_to must be provided together")

        all_xml_keys = [
            obj.key
            for obj in repo.s3.objects.filter(Prefix=repo.EXTRACTED_DIR).all()
            if _is_elsevier_main_xml_key(obj.key, repo)
        ]
        logger.info(
            "Found %s Elsevier extracted main.xml file(s) in %s",
            len(all_xml_keys),
            repo.EXTRACTED_DIR,
        )

        xml_bytes_cache = {}

        def _get_xml_bytes(key):
            if key not in xml_bytes_cache:
                xml_bytes_cache[key] = repo.get_by_id(key).getvalue()
            return xml_bytes_cache[key]

        def _sort_key(key):
            record_date = _extract_received_date_from_xml(_get_xml_bytes(key))
            return (record_date or date.min, key)

        if file_keys:
            resolved_keys = _resolve_file_keys(file_keys, all_xml_keys, repo)

            if target_dois:
                _log_if_xml_scan_exceeds_threshold(
                    len(resolved_keys),
                    "date extraction for sorting file_keys before DOI filtering",
                )
                resolved_keys = sorted(resolved_keys, key=_sort_key, reverse=True)
                _log_if_xml_scan_exceeds_threshold(
                    len(resolved_keys),
                    "DOI extraction from file_keys candidates",
                )
                found_dois = set()
                deduped_by_doi = {}

                for key in resolved_keys:
                    doi = _extract_doi_from_xml(_get_xml_bytes(key))
                    if not doi:
                        logger.warning("Could not extract DOI from file: %s", key)
                        continue

                    if doi not in target_dois:
                        continue

                    found_dois.add(doi)
                    if doi not in deduped_by_doi:
                        deduped_by_doi[doi] = key

                missing_dois = sorted(target_dois - found_dois)
                if missing_dois:
                    logger.warning(
                        "Some requested DOIs were not found: %s", missing_dois
                    )

                selected_keys = list(deduped_by_doi.values())
            else:
                selected_keys = resolved_keys

            _enforce_limit(selected_keys, limit)
            logger.info(
                "Selected %s Elsevier main.xml key(s) from file_keys (with glob expansion)",
                len(selected_keys),
            )
            return selected_keys

        if target_dois and not (date_from and date_to):
            date_to = date.today()
            date_from = date_to - timedelta(days=365)

        if not (date_from and date_to):
            raise ValueError(
                "Invalid parameters: provide either date_from+date_to, file_keys, or dois"
            )

        if target_dois and (date_to - date_from).days > 366:
            raise ValueError(
                "For DOI search the date range must not exceed one year. "
                "Please use a smaller range."
            )

        logger.info(
            "Selecting Elsevier main.xml files by XML ce:date-received range %s to %s",
            date_from,
            date_to,
        )

        selected_records = []
        _log_if_xml_scan_exceeds_threshold(
            len(all_xml_keys),
            "ce:date-received extraction from all main.xml candidates",
        )
        for key in all_xml_keys:
            record_date = _extract_received_date_from_xml(_get_xml_bytes(key))
            if record_date is None:
                continue
            if date_from <= record_date <= date_to:
                selected_records.append({"key": key, "record_date": record_date})

        selected_records.sort(
            key=lambda record: (record["record_date"], record["key"]),
            reverse=True,
        )

        logger.info(
            "Found %s Elsevier main.xml file(s) in the requested date range",
            len(selected_records),
        )

        if not target_dois:
            selected_keys = [record["key"] for record in selected_records]
            _enforce_limit(selected_keys, limit)
            logger.info("Selected %s Elsevier main.xml key(s)", len(selected_keys))
            return selected_keys

        found_dois = set()
        deduped_by_doi = {}

        _log_if_xml_scan_exceeds_threshold(
            len(selected_records),
            "DOI extraction after date-range filtering",
        )

        for record in selected_records:
            key = record["key"]
            doi = _extract_doi_from_xml(_get_xml_bytes(key))

            if not doi:
                logger.warning("Could not extract DOI from file: %s", key)
                continue

            if doi not in target_dois:
                continue

            found_dois.add(doi)
            if doi not in deduped_by_doi:
                deduped_by_doi[doi] = key

        missing_dois = sorted(target_dois - found_dois)
        if missing_dois:
            logger.warning("Some requested DOIs were not found: %s", missing_dois)

        selected_keys = list(deduped_by_doi.values())
        _enforce_limit(selected_keys, limit)

        logger.info(
            "Selected %s Elsevier main.xml key(s) after DOI filtering",
            len(selected_keys),
        )
        return selected_keys

    @task()
    def prepare_trigger_conf(file_keys, repo=ELSEVIER_REPO, **kwargs):
        dry_run = bool(kwargs.get("params", {}).get("dry_run", False))
        if dry_run:
            logger.info(
                "Dry run enabled. %s record(s) matched. No downstream runs will be triggered.",
                len(file_keys),
            )
            return []

        dataset_keys = {
            obj.key
            for obj in repo.s3.objects.filter(Prefix=repo.EXTRACTED_DIR).all()
            if os.path.basename(obj.key) == "dataset.xml"
        }
        requested_file_keys = set(file_keys)
        resolved_dataset_keys = []

        for key in file_keys:
            dataset_key = _find_dataset_key_for_xml_key(key, dataset_keys, repo)
            if not dataset_key:
                raise ValueError(f"Could not find sibling dataset.xml for file: {key}")
            if dataset_key not in resolved_dataset_keys:
                resolved_dataset_keys.append(dataset_key)

        all_confs = trigger_file_processing_elsevier(
            publisher="elsevier",
            repo=repo,
            logger=logger,
            filenames=resolved_dataset_keys,
        )
        confs = [conf for conf in all_confs if conf["file_name"] in requested_file_keys]

        prepared_file_keys = {conf["file_name"] for conf in confs}
        missing_file_keys = sorted(requested_file_keys - prepared_file_keys)
        if missing_file_keys:
            raise ValueError(
                f"Could not build Elsevier metadata for file(s): {missing_file_keys}"
            )

        logger.info("Prepared %s downstream trigger conf(s)", len(confs))
        return confs

    file_keys = collect_records()
    trigger_confs = prepare_trigger_conf(file_keys)

    TriggerDagRunOperator.partial(
        task_id="elsevier_reharvest_trigger_file_processing",
        trigger_dag_id="elsevier_process_file",
        reset_dag_run=True,
    ).expand(conf=trigger_confs)


elsevier_reharvest_dag = elsevier_reharvest()
