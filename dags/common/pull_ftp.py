import base64
import io
import logging
import os
import tarfile
import zipfile

from common.utils import process_archive

logger = logging.getLogger("airflow.task")


def migrate_files(
    archives_names,
    s_ftp,
    repo,
    logger,
    process_archives=True,
):
    logger.info("Processing files: %s", archives_names)
    extracted_or_downloaded_filenames = []
    for archive_name in archives_names:
        logger.info("Getting file from SFTP: %s", archive_name)
        file_bytes = s_ftp.get_file(archive_name)

        if (
            ".zip" in archive_name
            and zipfile.is_zipfile(file_bytes)
            or ".tar" in archive_name
            and tarfile.is_tarfile(file_bytes)
        ):
            if process_archives:
                for archive_file_content, s3_filename in process_archive(
                    file_bytes=file_bytes, file_name=archive_name
                ):
                    repo.save(s3_filename, io.BytesIO(archive_file_content))
                    if repo.is_meta(s3_filename):
                        extracted_or_downloaded_filenames.append(
                            os.path.join(repo.EXTRACTED_DIR, s3_filename)
                        )
                repo.save(archive_name, file_bytes)
            else:
                extracted_or_downloaded_filenames.append(
                    os.path.join(repo.RAW_DIR, archive_name)
                )
                repo.save(archive_name, file_bytes)

        else:
            logger.info(
                "File is not zip or tar, processing the next one: %s",
                archive_name,
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
    logger.info("Processing specified filenames.")
    filenames_pull_params = kwargs["params"]["filenames_pull"]
    filenames = filenames_pull_params["filenames"]
    return _find_files_in_zip(filenames, repo)


def _force_pull(
    s_ftp,
    repo,
    logger,
    **kwargs,
):
    logger.info("Force Pulling from SFTP.")
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
    logger.info("Pulling specified filenames from SFTP")
    return migrate_files(filenames, s_ftp, repo, logger)


def _find_files_in_zip(filenames, repo):
    extracted_filenames = []
    for zipped_filename in filenames:
        zipped_file = repo.get_by_id(f"{repo.RAW_DIR}{zipped_filename}")
        with zipfile.ZipFile(zipped_file) as zip:
            for zip_filename in zip.namelist():
                if repo.is_meta(zip_filename):
                    filename_without_extension = zipped_filename.split(".")[0]
                    extracted_filenames.append(
                        f"{repo.EXTRACTED_DIR}{filename_without_extension}/{zip_filename}"
                    )
    return extracted_filenames


def _differential_pull(
    s_ftp,
    repo,
    logger,
    **kwargs,
):
    logger.info("Pulling missing files only.")
    excluded_directories = kwargs["params"]["excluded_directories"]
    sftp_files = s_ftp.list_files(excluded_directories=excluded_directories)
    logger.info("SFTP files: %s", sftp_files)
    s3_files = repo.get_all_raw_filenames()
    logger.info("S3 files: %s", s3_files)
    diff_files = list(filter(lambda x: x not in s3_files, sftp_files))
    logger.info("Diff files: %s", diff_files)
    return migrate_files(diff_files, s_ftp, repo, logger)


def trigger_file_processing(
    publisher,
    repo,
    logger,
    filenames=None,
    article_splitter_function=lambda x: [x],
):
    confs = []
    if filenames is not None:
        files = filenames
    else:
        files = list(map(lambda x: x["xml"], repo.find_all()))

    if not files:
        logger.info("No files to process.")
        return []
    else:
        for filename in files:
            logger.info("Running processing for file: %s", filename)
            file_bytes = repo.get_by_id(filename)

            for article in article_splitter_function(file_bytes):
                encoded_article = base64.b64encode(article.getvalue()).decode()
                confs.append({"file": encoded_article, "file_name": filename})
        return confs
