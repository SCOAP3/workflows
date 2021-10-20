from dagster import solid
import ftputil

from workflows.utils.ftp_connection import ftp_session_factory
from workflows.constants import DUMMY_DIR


@solid(required_resource_keys={"ftp"})
def clean_ftp(context):
    parameters = context.resources.ftp
    ftp_host = ftputil.FTPHost(parameters["ftp_host"],
                               parameters["ftp_user"],
                               parameters["ftp_pass"],
                               session_factory=ftp_session_factory)
    ftp_host.use_list_a_option = False
    ftp_host.chdir(f'/{DUMMY_DIR}')

    ftp_host.remove('super_dummy_file2.zip')
    a = ftp_host.listdir('.')
    for b in a:
        context.log.info(b)