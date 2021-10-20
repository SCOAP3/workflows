import os


def get_ftp_resources_yaml_path(file_name):
    path_parts = __file__.split('/')
    base_path = '/'.join(path_parts[0:-2])
    sub_path_of_ftp_resources_yaml = f'resources/{file_name}'
    full_path_of_ftp_resources_yaml_file = os.path.join(base_path, sub_path_of_ftp_resources_yaml)
    return full_path_of_ftp_resources_yaml_file

