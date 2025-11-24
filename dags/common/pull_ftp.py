import base64
import io
import sys
import os
import tarfile
import zipfile
from datetime import datetime, timezone

from airflow.api.common import trigger_dag
from common.utils import process_archive
from structlog import PrintLogger


def migrate_files(
    archives_names,
    s_ftp,
    repo,
    logger: PrintLogger,
    process_archives=True,
):
    logger.msg("Processing files.", filenames=archives_names)
    extracted_or_downloaded_filenames = []
    for archive_name in archives_names:
        logger.msg("Getting file from SFTP.", file=archive_name)
        file_bytes = s_ftp.get_file(archive_name)

        if (
            ".zip" in archive_name
            and zipfile.is_zipfile(file_bytes)
            or ".tar" in archive_name
            and tarfile.is_tarfile(file_bytes)
        ):
            if process_archives:
                for (archive_file_content, s3_filename) in process_archive(
                    file_bytes=file_bytes, file_name=archive_name
                ):
                    repo.save(s3_filename, io.BytesIO(archive_file_content))
                    if repo.is_meta(s3_filename):
                        extracted_or_downloaded_filenames.append(
                            os.path.join("extracted/", s3_filename)
                        )
                repo.save(archive_name, file_bytes)
            else:
                extracted_or_downloaded_filenames.append(
                    os.path.join("raw", archive_name)
                )
                repo.save(archive_name, file_bytes)

        else:
            logger.info(
                "File is not zip or tar, processing the next one",
                file_name=archive_name,
            )
            continue
    return extracted_or_downloaded_filenames


def migrate_from_ftp(
    s_ftp,
    repo,
    logger,
    **kwargs,
):
    params = kwargs["params"]
    force_pull_specific_files = (
        "filenames_pull" in params
        and params["filenames_pull"]["enabled"]
        and params["filenames_pull"]["force_from_ftp"]
    )
    force_pull_all_files = (
        "filenames_pull" in params
        and not params["filenames_pull"]["enabled"]
        and params["force_pull"]
    )

    if force_pull_all_files:
        return _force_pull(s_ftp, repo, logger, **kwargs)
    elif force_pull_specific_files:
        return _filenames_pull(s_ftp, repo, logger, **kwargs)
    return _differential_pull(s_ftp, repo, logger, **kwargs)


def reprocess_files(repo, logger, **kwargs):
    logger.msg("Processing specified filenames.")
    filenames_pull_params = kwargs["params"]["filenames_pull"]
    filenames = filenames_pull_params["filenames"]
    return _find_files_in_extracted_dir(filenames, repo, logger)


def _force_pull(
    s_ftp,
    repo,
    logger,
    **kwargs,
):
    logger.msg("Force Pulling from SFTP.")
    excluded_directories = kwargs["params"]["excluded_directories"]
    filenames = s_ftp.list_files(excluded_directories=excluded_directories)
    return migrate_files(filenames, s_ftp, repo, logger)


def _filenames_pull(
    s_ftp,
    repo,
    logger,
    **kwargs,
):
    filenames_pull_params = kwargs["params"]["filenames_pull"]
    filenames = filenames_pull_params["filenames"]
    logger.msg("Pulling specified filenames from SFTP")
    return migrate_files(filenames, s_ftp, repo, logger)


def _find_files_in_tar(tar_filename, repo, logger):
    extracted_filenames = []
    logger.msg("Starting tar file reprocessing", tar_filename=tar_filename)
    tar_file = repo.get_by_id(f"raw/{tar_filename}")
    with tarfile.open(fileobj=tar_file, mode="r") as tar:
        for tar_inside_filename in tar.getnames():
            if repo.is_meta(tar_inside_filename):
                filename_without_extension = tar_filename.split(".")[0]
                extracted_filenames.append(
                    f"extracted/{filename_without_extension}/{tar_inside_filename}"
                )
    return extracted_filenames


def _find_files_in_zip(zipped_filename, repo, logger):
    extracted_filenames = []
    logger.msg("Starting zip file reprocessing", zipped_filename=zipped_filename)
    zipped_file = repo.get_by_id(f"raw/{zipped_filename}")
    with zipfile.ZipFile(zipped_file) as zip:
        for zip_filename in zip.namelist():
            if repo.is_meta(zip_filename):
                filename_without_extension = zipped_filename.split(".")[0]
                extracted_filenames.append(
                    f"extracted/{filename_without_extension}/{zip_filename}"
                )
    return extracted_filenames


def _find_files_in_extracted_dir(filenames, repo, logger):
    all_found_files = []
    for filename in filenames:
        if filename.endswith(".tar"):
            all_found_files.extend(_find_files_in_tar(filename, repo, logger))
        elif filename.endswith(".zip"):
            all_found_files.extend(_find_files_in_zip(filename, repo, logger))
        else:
            logger.msg("This file will be not processed. File is not an archive", filename=filename)
    logger.msg("Files that will be processed: ", all_found_files=all_found_files, filenames=filenames)
    return all_found_files


def _differential_pull(
    s_ftp,
    repo,
    logger,
    **kwargs,
):
    logger.msg("Pulling missing files only.")
    excluded_directories = kwargs["params"]["excluded_directories"]
    sftp_files = s_ftp.list_files(excluded_directories=excluded_directories)
    logger.msg(sftp_files)
    s3_files = repo.get_all_raw_filenames()
    logger.msg(s3_files)
    diff_files = list(filter(lambda x: x not in s3_files, sftp_files))
    logger.msg(diff_files)
    return migrate_files(diff_files, s_ftp, repo, logger)


def trigger_file_processing(
    publisher,
    repo,
    logger,
    filenames=None,
    article_splitter_function=lambda x: [x],
):
    files = []
    if filenames is not None:
        files = filenames
    else:
        files = list(map(lambda x: x["xml"], repo.find_all()))

    for filename in files:
        logger.msg("Running processing.", filename=filename)
        file_bytes = repo.get_by_id(filename)

        for article in article_splitter_function(file_bytes):
            _id = _generate_id(publisher)
            encoded_article = base64.b64encode(article.getvalue()).decode()
            trigger_dag.trigger_dag(
                dag_id=f"{publisher}_process_file",
                run_id=_id,
                conf={"file": encoded_article, "file_name": filename},
                replace_microseconds=False,
            )
    return files


def _generate_id(publisher):
    logs_date = datetime.now(timezone.utc)
    return f'{publisher}__{logs_date.strftime("%Y-%m-%dT%H:%M:%S.%f%z")}'
