import os
from dagster import solid, InputDefinition

from workflows.dagster_types import FTPDagsterType
from workflows.constants import LOCAL_FOLDER_FOR_DOWNLOADED_FILES


def upload_file(ftp, name):
    ftp.upload_if_newer(name, name)


@solid(required_resource_keys={"ftp"},
       input_defs=[InputDefinition(name='ftp', dagster_type=FTPDagsterType)])
def uploading_files_to_ftp(context, ftp):
    ftp_folder = context.resources.ftp["ftp_folder"]
    if os.path.exists(os.path.join(os.getcwd(), LOCAL_FOLDER_FOR_DOWNLOADED_FILES)):
        context.log.warn(f'{LOCAL_FOLDER_FOR_DOWNLOADED_FILES} folder already exists')
        pass
    else:
        os.mkdir(LOCAL_FOLDER_FOR_DOWNLOADED_FILES)

    # make sure that you're in root dir
    ftp.chdir('/')
    pwd = ftp.getcwd()
    if ftp.path.exists(ftp.path.join(pwd, ftp_folder)):
        context.log.warn(f'{ftp_folder} already exists')
        pass
    else:
        ftp.mkdir(ftp_folder)
        context.log.info(f'Created {ftp_folder}')

    ftp.chdir(ftp_folder)
    path = ftp.getcwd()

    # uploading example file to ftp server
    
    ftp.upload_if_newer('oup.xml.zip', 'oup.xml.zip')
    ftp.upload_if_newer('scoap3.archival.zip', 'scoap3.archival.zip')
    ftp.upload_if_newer('scoap3.pdf.zip', 'scoap3.pdf.zip')

    dirs_list = ftp.listdir(path)

    context.log.info(f'Dummy file was moved to {path}: files/dirs there: {str(dirs_list)}')
