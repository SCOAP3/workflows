import os
from dagster import solid, InputDefinition, OutputDefinition
from time import localtime, strftime

from workflows.constants import LOCAL_FOLDER_FOR_DOWNLOADED_FILES
from workflows.dagster_types import FTPDagsterType


def get_files_to_download(specific_files, all_files):
    if len(specific_files) > 0:
        return specific_files
    else:
        return all_files


@solid(
    required_resource_keys={"download_a_file_from_ftp"},
    input_defs=[
    InputDefinition(name='ftp', dagster_type=FTPDagsterType),
    InputDefinition(name="files_paths", dagster_type=list)],
    output_defs=[OutputDefinition(list)])

def download_a_file_from_ftp(context, ftp, files_paths):
    specific_files_paths = context.resources.download_a_file_from_ftp["specific_files_paths"]
    context.log.error(files_paths)
    files_paths_to_download = get_files_to_download(specific_files_paths, files_paths)
    # come back to root dir, because file which will be downloaded have absolute path
    ftp.chdir('/')
    # where downloaded files will be saved
    target_folder = os.path.abspath(os.path.join(os.getcwd(), LOCAL_FOLDER_FOR_DOWNLOADED_FILES))
    filename_prefix = strftime('%Y-%m-%d_%H:%M:%S', localtime())
    local_filenames = []
    for file_path in files_paths_to_download:
        new_file_name = '%s_%s' % (filename_prefix, os.path.basename(file_path))
        local_filename = os.path.join(target_folder, new_file_name)

        dir_name = os.path.dirname(file_path)
        ftp.download_if_newer(file_path, local_filename)
        context.log.info(f'File {new_file_name} with path {dir_name} to {target_folder}')
        local_filenames.append(local_filename)

    return local_filenames


    