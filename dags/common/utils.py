import io
import json
import os
import re
import tarfile
import xml.etree.ElementTree as ET
import zipfile
from datetime import date, datetime
from ftplib import error_perm
from io import StringIO
from stat import S_ISDIR, S_ISREG

import backoff
import country_converter as coco
import pycountry
import requests
from airflow.models.dagrun import DagRun
from airflow.utils.state import DagRunState
from common.constants import (
    BY_PATTERN,
    CDATA_PATTERN,
    CHAR_REPLACEMENTS,
    COUNTRIES_DEFAULT_MAPPING,
    CREATIVE_COMMONS_PATTERN,
    LICENSE_PATTERN,
    SPECIAL_CASES,
    SPECIAL_PATTERNS,
)
from common.exceptions import UnknownFileExtension, UnknownLicense
from inspire_utils.record import get_value
from structlog import get_logger

logger = get_logger()
cc = coco.CountryConverter()


def set_harvesting_interval(repo, **kwargs):
    if (
        "params" in kwargs
        and kwargs["params"].get("from_date")
        and kwargs["params"].get("until_date")
    ):
        return {
            "from_date": kwargs["params"]["from_date"],
            "until_date": kwargs["params"]["until_date"],
        }
    from_date = (
        kwargs.get("params", {}).get("from_date")
        or repo.find_the_last_uploaded_file_date()
    )
    until_date = date.today().strftime("%Y-%m-%d")
    return {
        "from_date": (from_date or until_date),
        "until_date": until_date,
    }


def is_json_serializable(x):
    try:
        json.dumps(x)
        return True
    except TypeError:
        return False


def check_value(value):
    json_serializable = is_json_serializable(value)
    if json_serializable:
        if value:
            return bool(value)
        if "hasattr" in dir(value) and value.hasattr("__iter__"):
            return all(value)
        return False
    return False


def parse_to_int(value):
    try:
        return int(value)
    except (ValueError, TypeError):
        logger.error("Cannot parse to integer", value=value)


def extract_text(article, path, field_name, dois):
    try:
        return article.find(path).text
    except AttributeError:
        logger.error(f"{field_name} is not found in XML", dois=dois)
        return


def append_not_excluded_files(filename, exclude_directories, list_of_files):
    if not exclude_directories or not (
        any(re.search(exclude, filename) for exclude in exclude_directories)
    ):
        list_of_files.append(filename)


def find_extension(file):
    if file.endswith(".xml"):
        return "xml"
    elif file.endswith(".pdf"):
        return "pdf"
    raise UnknownFileExtension(file)


def walk_sftp(sftp, remotedir, paths):
    for entry in sftp.listdir_attr(remotedir):
        remotepath = remotedir + "/" + entry.filename
        mode = entry.st_mode
        if S_ISDIR(mode):
            walk_sftp(sftp=sftp, remotedir=remotepath, paths=paths)
        elif S_ISREG(mode):
            paths.append(remotepath)


def walk_ftp(ftp, remotedir, paths):
    for entry in ftp.nlst(remotedir):
        try:
            ftp.cwd(entry)
            walk_ftp(ftp=ftp, remotedir=entry, paths=paths)
        except error_perm:
            ftp.cwd("/")
            paths.append(os.path.basename(entry))


def construct_license(license_type, version, url=None):
    if not license_type == "CC-BY":
        raise UnknownLicense(license_type)
    if url and license_type and version:
        return {"url": url, "license": f"{license_type}-{version}"}
    if license_type and version:
        logger.error("License URL is not found in XML.")
        return {"license": f"{license_type}-{version}"}
    logger.error(
        "License is not given, or missing arguments.",
    )


def get_license_type(license_text):
    if not CREATIVE_COMMONS_PATTERN.search(license_text) or not BY_PATTERN.match(
        license_text
    ):
        raise UnknownLicense(license=license_text)
    return "CC-BY"


def get_license_type_and_version_from_url(url):
    match = LICENSE_PATTERN.search(url)
    if not match:
        logger.error("No license found in URL")
        return None
    first_part_of_license_type = ""
    version = match.group(2)
    second_part_of_license_type = match.group(1).upper()
    if CREATIVE_COMMONS_PATTERN.search(url):
        first_part_of_license_type = "CC"
    else:
        raise UnknownLicense(url)
    if not f"{first_part_of_license_type}-{second_part_of_license_type}" == "CC-BY":
        raise UnknownLicense(url)
    license_type = ("-").join([first_part_of_license_type, second_part_of_license_type])
    return construct_license(license_type=license_type, version=version, url=url)


def preserve_cdata(article):
    matches = CDATA_PATTERN.finditer(article)
    for match in matches:
        cdata_content_with_escaped_escape_chars = match.group(1).replace("\\", "\\\\")
        article = CDATA_PATTERN.sub(
            cdata_content_with_escaped_escape_chars, article, count=1
        )
    return article


def parse_to_ET_element(article):
    return ET.fromstring(preserve_cdata(article))


def remove_xml_namespaces(xml_content_bytes):
    if isinstance(xml_content_bytes, bytes):
        xml_content = xml_content_bytes.decode("utf-8")
    else:
        xml_content = xml_content_bytes

    cleaned_content = re.sub(r"<(/?)([^:>\s]+):([^>\s]+)", r"<\1\3", xml_content)

    return cleaned_content


def parse_without_names_spaces(xml):
    try:
        if type(xml) == str:
            it = ET.iterparse(StringIO(xml))
        else:
            it = ET.iterparse(xml, events=("start", "end"))
        for _, el in it:
            el.tag = el.tag.rpartition("}")[-1]
        root = it.root
    except ET.ParseError:
        if isinstance(xml, io.BytesIO):
            xml = xml.getvalue().decode("utf-8")
        xml = remove_xml_namespaces(xml)
        if type(xml) == str:
            it = ET.iterparse(StringIO(xml))
        else:
            it = ET.iterparse(StringIO(xml.getvalue().decode("utf-8")))
        for _, el in it:
            el.tag = el.tag.rpartition("}")[-1]
        root = it.root
    return root


def get_text_value(element):
    if element is not None:
        if element.text:
            return clean_text(element.text)


def clean_text(text):
    return " ".join(text.split())


def check_dagrun_state(dagrun: DagRun, not_allowed_states=[], allowed_states=[]):
    dag_run_states = {
        "queued": DagRunState.QUEUED,
        "running": DagRunState.RUNNING,
        "failed": DagRunState.FAILED,
    }
    dagrun.update_state()
    states_values = []

    for not_allowed_state in not_allowed_states:
        value = dagrun.get_state() != dag_run_states[not_allowed_state]
        states_values.append(value)
    for allowed_state in allowed_states:
        value = dagrun.get_state() == dag_run_states[allowed_state]
        states_values.append(value)
    return all(states_values)


def process_zip_file(file_bytes, file_name, **kwargs):
    file_bytes.seek(0)
    only_specific_file = kwargs.get("only_specific_file")
    with zipfile.ZipFile(file_bytes) as zip:
        for filename in zip.namelist():
            if only_specific_file and only_specific_file not in filename:
                continue
            zip_file_content = zip.read(filename)
            file_prefix = ".".join(file_name.split(".")[:-1])
            s3_filename = os.path.join(file_prefix, filename)
            yield (zip_file_content, s3_filename)


def process_tar_file(file_bytes, file_name, **kwargs):
    file_bytes.seek(0)
    only_specific_file = kwargs.get("only_specific_file")
    with tarfile.open(fileobj=file_bytes, mode="r") as tar:
        for filename in tar.getnames():
            if only_specific_file and only_specific_file not in filename:
                continue
            tar_file_content = tar.extractfile(filename).read()
            file_prefix = ".".join(file_name.split(".")[:-1])
            s3_filename = os.path.join(file_prefix, filename)
            yield (tar_file_content, s3_filename)


def process_archive(file_bytes, file_name, **kwargs):
    if zipfile.is_zipfile(file_bytes):
        return process_zip_file(file_bytes, file_name, **kwargs)
    if tarfile.is_tarfile(file_bytes):
        return process_tar_file(file_bytes, file_name, **kwargs)


def parse_element_text(item):
    title_parts = []

    def iterate_element(item):
        if item.tag in ["xref"]:
            return
        if item.tag in ["math"]:
            return
        if item.text:
            title_parts.append(item.text.strip())
        for subitem in item:
            iterate_element(subitem)
        if item.tail:
            title_parts.append(item.tail.strip())

    iterate_element(item)

    title_part = [i for i in title_parts if i]
    full_text = " ".join(title_part).strip()

    return full_text


@backoff.on_exception(
    backoff.expo,
    (requests.exceptions.ConnectionError, requests.exceptions.Timeout),
    max_tries=5,
)
def create_or_update_article(data):
    logger.info("Sending data to the backend", data=data)
    backend_url = os.getenv(
        "BACKEND_URL", "http://localhost:8000/api/article-workflow-import/"
    )
    token = os.getenv("BACKEND_TOKEN", "CHANGE_ME")
    headers = {"Content-Type": "application/json", "Authorization": f"Token {token}"}
    response = requests.post(
        f"{backend_url}",
        data=json.dumps(data),
        headers=headers,
    )
    try:
        response.raise_for_status()
        return response.json()
    except requests.HTTPError:
        logger.error(response.content)
        raise


def check_special_cases(normalized_value):
    match = SPECIAL_PATTERNS.search(normalized_value)
    if not match:
        return None
    return SPECIAL_CASES[match.group(1)]


def unwrap_country_converter_result(converter_result):
    if isinstance(converter_result, (list, tuple)):
        for item in converter_result:
            if isinstance(item, str) and item.lower() != "not found":
                return item
        return None
    if not converter_result or converter_result.lower() == "not found":
        return None
    return converter_result


def match_with_country_converter_results(normalized_value):
    raw_iso2_result = cc.convert(names=normalized_value, to="ISO2")
    iso2_code = unwrap_country_converter_result(raw_iso2_result)
    if not iso2_code:
        return None
    raw_short_name = cc.convert(names=iso2_code, to="name_short")
    country_short_name = unwrap_country_converter_result(raw_short_name)
    if country_short_name:
        return country_short_name


def fuzzy_search_country(normalized_value):
    normalized_name_parts = normalized_value.split()
    normalized_name_parts_length = len(normalized_name_parts)
    max_phrase_length = min(6, normalized_name_parts_length)

    for skip_from_end in range(normalized_name_parts_length):
        for phrase_length in range(max_phrase_length, 0, -1):
            phrase_start_index = (
                normalized_name_parts_length - skip_from_end - phrase_length
            )
            if phrase_start_index < 0:
                continue
            phrase_end_index = normalized_name_parts_length - skip_from_end
            search_phrase = " ".join(
                normalized_name_parts[phrase_start_index:phrase_end_index]
            )
            try:
                fuzzy_matches = pycountry.countries.search_fuzzy(search_phrase)
                if fuzzy_matches:
                    return unwrap_country_converter_result(
                        cc.convert(names=fuzzy_matches[0].alpha_2, to="name_short")
                    )
            except LookupError:
                continue


def parse_country_from_value(value):
    normalized_value = value.lower().translate(CHAR_REPLACEMENTS)

    special_case_country = check_special_cases(normalized_value)
    if special_case_country:
        return special_case_country

    converter_country = match_with_country_converter_results(normalized_value)
    if converter_country:
        return converter_country

    return fuzzy_search_country(normalized_value)


def get_country_ISO_name(country):
    if COUNTRIES_DEFAULT_MAPPING.get(country):
        return COUNTRIES_DEFAULT_MAPPING[country]
    else:
        return country


def upload_json_to_s3(json_record, repo):
    file_in_bytes = io.BytesIO(json.dumps(json_record, indent=2).encode("utf-8"))
    current_date = datetime.now().date()
    current_date_str = current_date.strftime("%Y-%m-%d")
    current_date_and_time_str = current_date.strftime("%Y-%m-%d_%H:%M:%S")
    doi = get_value(json_record, "dois.value[0]")
    file_key = os.path.join(
        "parsed", current_date_str, f"{doi}__{current_date_and_time_str}.json"
    )
    repo.save(file_key, file_in_bytes)
