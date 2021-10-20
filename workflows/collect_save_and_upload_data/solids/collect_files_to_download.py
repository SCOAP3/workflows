import os
from dagster import solid, InputDefinition, DynamicOutputDefinition, OutputDefinition, Nothing
from workflows.dagster_types import FTPDagsterType


from workflows.utils.generators import generate_mapping_key

# Passing Nothing type variable:
# Solids create_dummy_dir and collect_files_to_download are not depending on each other, because
# create_dummy_dir doesn't return any output which is needed for collect_files_to_download solid.
# In this way solids are ran parallel. However, we want to have dummy files created first, so
# we passing Nothing as an output from create_dummy_dir to collect_files_to_download to set the order of solids.

@solid(required_resource_keys={"ftp"},
       input_defs=[InputDefinition(name='ftp', dagster_type=FTPDagsterType),
                   InputDefinition("start", Nothing)
                   ],
       output_defs=[OutputDefinition(list)])
def collect_files_to_download(context, ftp) -> list:
    """
    Collects all the files in under the 'ftp_folder' folder.
    Files starting with a dot (.) are omitted.
    :ftp FTPHost:
    :return: list of all found file's path
    """

    # make sure you're in root dir
    ftp.chdir('/')
    result = []
    ftp_folder = context.resources.ftp["ftp_folder"]
    for path, dirs, files in ftp.walk(ftp_folder):
        for filename in files:
            if filename.startswith('.'):
                continue
            full_path = os.path.join(path, filename)
            context.log.info(full_path)
            if filename.endswith('.zip') or filename == 'go.xml':
                result.append(full_path)
                # yield DynamicOutput(value={'file_path': full_path, 'ftp': ftp},
                #                     mapping_key=generate_mapping_key())
            else:
                context.log.warning(f'File with invalid extension on FTP path={full_path}')
    return result


