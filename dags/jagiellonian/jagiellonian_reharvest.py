import fnmatch
import json
import logging
import re
from datetime import date, datetime, timedelta

import pendulum
from airflow.providers.standard.operators.trigger_dagrun import TriggerDagRunOperator
from airflow.sdk import Param, dag, task
from common.notification_service import FailedDagNotifier
from jagiellonian.repository import JagiellonianRepository

logger = logging.getLogger("airflow.task")
JAGIELLONIAN_REPO = JagiellonianRepository()

_FILENAME_DATE_PATTERN = re.compile(r"_metadata_(\d{4}-\d{2}-\d{2})")
_FILENAME_DATETIME_PATTERN = re.compile(
    r"_metadata_(\d{4}-\d{2}-\d{2})[ T](\d{2})[:_](\d{2})[:_](\d{2})"
)


def _parse_date(value):
    if not value:
        return None
    return datetime.strptime(value, "%Y-%m-%d").date()


def _normalize_dois(dois):
    if not dois:
        return set()
    return {doi.strip().lower() for doi in dois if isinstance(doi, str) and doi.strip()}


def _normalize_file_keys(file_keys):
    return [k.strip() for k in file_keys if isinstance(k, str) and k.strip()]


def _extract_date_from_key(key):
    if not key:
        return None

    match = _FILENAME_DATE_PATTERN.search(key)
    if not match:
        return None

    try:
        return datetime.strptime(match.group(1), "%Y-%m-%d").date()
    except ValueError:
        return None


def _extract_datetime_from_key(key):
    if not key:
        return datetime.min

    match = _FILENAME_DATETIME_PATTERN.search(key)
    if not match:
        return datetime.min

    try:
        return datetime.strptime(
            f"{match.group(1)} {match.group(2)}:{match.group(3)}:{match.group(4)}",
            "%Y-%m-%d %H:%M:%S",
        )
    except ValueError:
        return datetime.min


def _extract_doi_from_json(article_json):
    if not isinstance(article_json, dict):
        return None

    doi_entries = article_json.get("dois") or []
    if isinstance(doi_entries, list):
        for doi_entry in doi_entries:
            if isinstance(doi_entry, dict):
                value = doi_entry.get("value")
                if isinstance(value, str) and value.strip():
                    return value.strip().lower()
            elif isinstance(doi_entry, str) and doi_entry.strip():
                return doi_entry.strip().lower()

    raw_doi = article_json.get("DOI")
    if isinstance(raw_doi, str) and raw_doi.strip():
        return raw_doi.strip().lower()

    return None


def _is_glob_pattern(value):
    return any(c in value for c in ("*", "?", "["))


def _resolve_file_keys(file_keys, all_json_keys):
    all_json_keys_set = set(all_json_keys)

    exact_keys = [k for k in file_keys if not _is_glob_pattern(k)]
    glob_patterns = [k for k in file_keys if _is_glob_pattern(k)]

    missing = [k for k in exact_keys if k not in all_json_keys_set]
    if missing:
        raise ValueError(f"Some requested file_keys do not exist: {missing}")

    resolved = list(exact_keys)

    for pattern in glob_patterns:
        matched = [key for key in all_json_keys if fnmatch.fnmatch(key, pattern)]
        if not matched:
            logger.warning(
                "Pattern %r matched no Jagiellonian metadata JSON keys", pattern
            )
        resolved.extend(matched)

    seen = set()
    deduped = []
    for key in resolved:
        if key not in seen:
            seen.add(key)
            deduped.append(key)
    return deduped


def _enforce_limit(records, limit):
    if limit is None:
        return
    if len(records) > limit:
        raise ValueError(
            f"Matched {len(records)} records, which is above limit={limit}. "
            "Please reduce the date range or increase the limit."
        )


@dag(
    on_failure_callback=FailedDagNotifier(),
    start_date=pendulum.today("UTC").add(days=-1),
    schedule=None,
    catchup=False,
    tags=["reharvest", "jagiellonian"],
    params={
        "date_from": Param(
            default=None,
            type=["string", "null"],
            description="Start date in YYYY-MM-DD format (from metadata filename)",
            title="Date from",
        ),
        "date_to": Param(
            default=None,
            type=["string", "null"],
            description="End date in YYYY-MM-DD format (from metadata filename)",
            title="Date to",
        ),
        "file_keys": Param(
            default=[],
            type=["array", "null"],
            description=(
                "Exact Jagiellonian metadata JSON keys or glob patterns. "
                "Example: '*' or '10.5506/*_metadata_2026-04-09*.json'."
            ),
            title="File keys",
        ),
        "dois": Param(
            default=[],
            type=["array", "null"],
            description=(
                "List of DOIs to process. DOI is extracted from metadata JSON at "
                "dois[].value. If date_from/date_to are not provided, this will search "
                "only records from the last 3 years."
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
def jagiellonian_reharvest():
    @task()
    def collect_records(repo=JAGIELLONIAN_REPO, **kwargs):
        params = kwargs.get("params", {})

        date_from = _parse_date(params.get("date_from"))
        date_to = _parse_date(params.get("date_to"))
        file_keys = _normalize_file_keys(params.get("file_keys") or [])
        dois = _normalize_dois(params.get("dois") or [])
        target_dois = set(dois)
        limit = params.get("limit")

        if limit is not None and (not isinstance(limit, int) or limit <= 0):
            raise ValueError("limit must be a positive integer when provided")

        if bool(file_keys) and (date_from or date_to):
            raise ValueError(
                "Invalid parameters: date_from/date_to cannot be used together with file_keys"
            )

        if (date_from and not date_to) or (date_to and not date_from):
            raise ValueError("Both date_from and date_to must be provided together")

        all_json_keys = [
            obj.key for obj in repo.s3_bucket.objects.all() if obj.key.endswith(".json")
        ]

        logger.info(
            "Found %s Jagiellonian metadata JSON file(s) in storage", len(all_json_keys)
        )

        if file_keys:
            resolved_keys = _resolve_file_keys(file_keys, all_json_keys)
        else:
            if target_dois and not (date_from and date_to):
                date_to = date.today()
                date_from = date_to - timedelta(days=365 * 3)

            if not (date_from and date_to):
                raise ValueError(
                    "Invalid parameters: provide either date_from+date_to, file_keys, or dois"
                )

            logger.info(
                "Selecting Jagiellonian metadata JSON in date range %s to %s",
                date_from,
                date_to,
            )

            resolved_keys = []
            for key in all_json_keys:
                key_date = _extract_date_from_key(key)
                if key_date is None:
                    continue
                if date_from <= key_date <= date_to:
                    resolved_keys.append(key)

        resolved_keys = sorted(
            resolved_keys, key=_extract_datetime_from_key, reverse=True
        )

        deduped_by_doi = {}
        keys_without_doi = []
        found_dois = set()

        for key in resolved_keys:
            article_json = json.loads(repo.get_by_id(key).getvalue().decode("utf-8"))
            doi = _extract_doi_from_json(article_json)

            if not doi:
                logger.warning("Could not extract DOI from metadata JSON: %s", key)
                if not target_dois:
                    keys_without_doi.append({"key": key, "article": article_json})
                continue

            if target_dois and doi not in target_dois:
                continue

            if target_dois:
                found_dois.add(doi)

            if doi not in deduped_by_doi:
                deduped_by_doi[doi] = {"key": key, "article": article_json}

        if target_dois:
            missing_dois = sorted(target_dois - found_dois)
            if missing_dois:
                logger.warning("Some requested DOIs were not found: %s", missing_dois)

        selected_records = list(deduped_by_doi.values()) + keys_without_doi
        _enforce_limit(selected_records, limit)

        logger.info(
            "Collected %s deduplicated Jagiellonian record(s)", len(selected_records)
        )
        logger.info(
            "Selected Jagiellonian metadata keys: %s",
            [r["key"] for r in selected_records],
        )

        return [record["article"] for record in selected_records]

    @task()
    def prepare_trigger_conf(records, **kwargs):
        dry_run = bool(kwargs.get("params", {}).get("dry_run", False))
        if dry_run:
            logger.info(
                "Dry run enabled. %s record(s) matched. No downstream runs will be triggered.",
                len(records),
            )
            return []

        confs = [{"article": record} for record in records]
        logger.info("Prepared %s downstream trigger conf(s)", len(confs))
        return confs

    records = collect_records()
    trigger_confs = prepare_trigger_conf(records)

    TriggerDagRunOperator.partial(
        task_id="jagiellonian_reharvest_trigger_file_processing",
        trigger_dag_id="jagiellonian_process_file",
        reset_dag_run=True,
    ).expand(conf=trigger_confs)


jagiellonian_reharvest_dag = jagiellonian_reharvest()
