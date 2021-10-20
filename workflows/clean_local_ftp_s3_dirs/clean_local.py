from dagster import solid
import os
import glob


@solid
def clean_local(context):
    downloaded_dir = "downloaded"
    downloaded_from_ftp_dir = "downloaded_from_ftp"
    base_path = '/'.join((os.path.dirname(__file__)).split('/')[:-2])
    downloaded_dir_path = os.path.join(base_path, downloaded_dir)
    downloaded_from_ftp_dir_path = os.path.join(base_path, downloaded_from_ftp_dir)
    files_in_downloaded_dir = glob.glob(f'{downloaded_dir_path}/*')
    files_in_downloaded_from_FTP_dir = glob.glob(f'{downloaded_from_ftp_dir_path}/*')

    for f in files_in_downloaded_dir:
        os.remove(f)

    for f in files_in_downloaded_from_FTP_dir:
        os.remove(f)

    return context.log.info('Local directories are cleaned')

