import os
from dagster import solid, InputDefinition, String, OutputDefinition, DynamicOutput
import zipfile

from workflows.utils.create_dir import create_dir
from workflows.constants import UNZIPPED_FILES
from workflows.utils.generators import generate_mapping_key


@solid(input_defs=[InputDefinition(name="file_paths", dagster_type=list)],
       output_defs=[OutputDefinition(list)])
def unzip(context, file_paths):
    cwd = os.getcwd()
    dir_is_created = create_dir(context, cwd, UNZIPPED_FILES)

    paths_for_unzipped_files = []
    for file_path in file_paths:
        file_name = os.path.basename(file_path)
        grouping_folder = file_name.split(".zip")[0]
        path_for_unzipped_files = os.path.join(cwd, UNZIPPED_FILES, grouping_folder)
        with zipfile.ZipFile(file_path, 'r') as zip_ref:
            try:
                zip_ref.extractall(path_for_unzipped_files)
                context.log.info(f'file {file_path} is extracted successfully')
                paths_for_unzipped_files.append(path_for_unzipped_files)
            except Exception as e:
                context.log.info(f'Error while extracting the file {file_path}: {e}')
    return paths_for_unzipped_files
