import base64
import fnmatch
import logging
import re
from datetime import date, datetime, timedelta

import pendulum
from airflow.providers.standard.operators.trigger_dagrun import TriggerDagRunOperator
from airflow.sdk import Param, dag, task
from common.notification_service import FailedDagNotifier
from common.utils import parse_without_names_spaces
from springer.repository import SpringerRepository

logger = logging.getLogger("airflow.task")
SPRINGER_REPO = SpringerRepository()
_ARCHIVE_DT_PATTERN = re.compile(r"ftp_PUB_(\d{2}-\d{2}-\d{2})_(\d{2}-\d{2}-\d{2})")


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


def _is_glob_pattern(value):
    return any(c in value for c in ("*", "?", "["))


def _extract_archive_datetime_from_key(key):
    if not key:
        return datetime.min

    match = _ARCHIVE_DT_PATTERN.search(key)
    if not match:
        return datetime.min

    try:
        return datetime.strptime(
            f"{match.group(1)}_{match.group(2)}", "%y-%m-%d_%H-%M-%S"
        )
    except ValueError:
        return datetime.min


def _extract_archive_date_from_key(key):
    dt_value = _extract_archive_datetime_from_key(key)
    if dt_value == datetime.min:
        return None
    return dt_value.date()


def _extract_doi_from_xml(xml_bytes):
    try:
        if isinstance(xml_bytes, bytes):
            xml_text = xml_bytes.decode("utf-8")
        else:
            xml_text = xml_bytes
        xml = parse_without_names_spaces(xml_text)
        doi_element = xml.find("./Journal/Volume/Issue/Article/ArticleInfo/ArticleDOI")
        if doi_element is not None and doi_element.text:
            return doi_element.text.strip().lower()
    except Exception:
        pass
    return None


def _resolve_file_keys(file_keys, all_xml_keys):
    all_xml_keys_set = set(all_xml_keys)
    prefix = SPRINGER_REPO.EXTRACTED_DIR

    exact_keys = [k for k in file_keys if not _is_glob_pattern(k)]
    glob_patterns = [k for k in file_keys if _is_glob_pattern(k)]

    missing = [k for k in exact_keys if k not in all_xml_keys_set]
    if missing:
        raise ValueError(f"Some requested file_keys do not exist: {missing}")

    resolved = list(exact_keys)

    for pattern in glob_patterns:
        matched = [
            key
            for key in all_xml_keys
            if fnmatch.fnmatch(
                key[len(prefix) :] if key.startswith(prefix) else key, pattern
            )
        ]
        if not matched:
            logger.warning("Pattern %r matched no Springer extracted XML keys", pattern)
        resolved.extend(matched)

    seen = set()
    deduped = []
    for key in resolved:
        if key not in seen:
            seen.add(key)
            deduped.append(key)
    return deduped


def _filter_keys_by_dois(keys, target_dois, repo):
    deduped = {}
    found_dois = set()

    for key in keys:
        file_obj = repo.get_by_id(key)
        doi = _extract_doi_from_xml(file_obj.getvalue())

        if not doi:
            logger.warning("Could not extract DOI from file: %s", key)
            continue

        if doi not in target_dois:
            continue

        found_dois.add(doi)
        if doi not in deduped:
            deduped[doi] = key

    missing_dois = sorted(target_dois - found_dois)
    if missing_dois:
        logger.warning("Some requested DOIs were not found: %s", missing_dois)

    return list(deduped.values())


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
    tags=["reharvest", "springer"],
    params={
        "date_from": Param(
            default=None,
            type=["string", "null"],
            description="Start date from extracted archive folder in YYYY-MM-DD format",
            title="Date from",
        ),
        "date_to": Param(
            default=None,
            type=["string", "null"],
            description="End date from extracted archive folder in YYYY-MM-DD format",
            title="Date to",
        ),
        "file_keys": Param(
            default=[],
            type=["array", "null"],
            description=(
                "Exact Springer extracted XML keys or glob patterns matched relative "
                f"to '{SPRINGER_REPO.EXTRACTED_DIR}'. Examples: '*' or "
                f"'EPJC/ftp_PUB_26-03-29_20-00-46/*'."
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
def springer_reharvest():
    @task()
    def collect_records(repo=SPRINGER_REPO, **kwargs):
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

        all_xml_keys = [
            obj.key
            for obj in repo.s3.objects.filter(Prefix=repo.EXTRACTED_DIR).all()
            if repo.is_meta(obj.key)
        ]
        logger.info(
            "Found %s Springer extracted XML file(s) in %s",
            len(all_xml_keys),
            repo.EXTRACTED_DIR,
        )

        if file_keys:
            resolved_keys = _resolve_file_keys(file_keys, all_xml_keys)

            if target_dois:
                resolved_keys = sorted(
                    resolved_keys,
                    key=_extract_archive_datetime_from_key,
                    reverse=True,
                )
                selected_keys = _filter_keys_by_dois(
                    keys=resolved_keys,
                    target_dois=target_dois,
                    repo=repo,
                )
            else:
                selected_keys = resolved_keys

            _enforce_limit(selected_keys, limit)
            logger.info(
                "Selected %s Springer XML key(s) from file_keys (with glob expansion)",
                len(selected_keys),
            )
            return selected_keys

        if dois and not (date_from and date_to):
            date_to = date.today()
            date_from = date_to - timedelta(days=365)

        if not (date_from and date_to):
            raise ValueError(
                "Invalid parameters: provide either date_from+date_to, file_keys, or dois"
            )

        if dois and (date_to - date_from).days > 366:
            raise ValueError(
                "For DOI search the date range must not exceed one year. "
                "Please use a smaller range."
            )

        logger.info(
            "Selecting Springer extracted XML files in date range %s to %s",
            date_from,
            date_to,
        )

        keys_in_range = []
        for key in all_xml_keys:
            key_date = _extract_archive_date_from_key(key)
            if key_date is None:
                continue
            if date_from <= key_date <= date_to:
                keys_in_range.append(key)

        keys_in_range.sort(key=_extract_archive_datetime_from_key, reverse=True)

        logger.info(
            "Found %s Springer extracted XML file(s) in the requested date range",
            len(keys_in_range),
        )

        deduped = {}
        keys_without_doi = []
        found_dois = set()

        for key in keys_in_range:
            file_obj = repo.get_by_id(key)
            doi = _extract_doi_from_xml(file_obj.getvalue())

            if not doi:
                logger.warning("Could not extract DOI from file: %s", key)
                if not target_dois:
                    keys_without_doi.append(key)
                continue

            if target_dois and doi not in target_dois:
                continue

            if target_dois:
                found_dois.add(doi)

            if doi not in deduped:
                deduped[doi] = key

        if target_dois:
            missing_dois = sorted(target_dois - found_dois)
            if missing_dois:
                logger.warning("Some requested DOIs were not found: %s", missing_dois)

        selected_keys = list(deduped.values()) + keys_without_doi

        _enforce_limit(selected_keys, limit)
        logger.info("Collected %s deduplicated Springer XML key(s)", len(selected_keys))
        logger.info("Selected Springer XML keys: %s", selected_keys)
        return selected_keys

    @task()
    def prepare_trigger_conf(file_keys, repo=SPRINGER_REPO, **kwargs):
        dry_run = bool(kwargs.get("params", {}).get("dry_run", False))
        if dry_run:
            logger.info(
                "Dry run enabled. %s record(s) matched. No downstream runs will be triggered.",
                len(file_keys),
            )
            return []

        confs = []
        for key in file_keys:
            file_obj = repo.get_by_id(key)
            encoded_xml = base64.b64encode(file_obj.getvalue()).decode("utf-8")
            confs.append({"file": encoded_xml, "file_name": key})

        logger.info("Prepared %s downstream trigger conf(s)", len(confs))
        return confs

    file_keys = collect_records()
    trigger_confs = prepare_trigger_conf(file_keys)

    TriggerDagRunOperator.partial(
        task_id="springer_reharvest_trigger_file_processing",
        trigger_dag_id="springer_process_file",
        reset_dag_run=True,
    ).expand(conf=trigger_confs)


springer_reharvest_dag = springer_reharvest()
