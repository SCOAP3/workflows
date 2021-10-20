from dagster import solid
import ftputil

from workflows.utils.ftp_connection import ftp_session_factory


@solid(required_resource_keys={"ftp"})
def connect_to_ftp_server(context) -> ftputil.FTPHost:
    parameters = context.resources.ftp

    ftp_host = ftputil.FTPHost(parameters["ftp_host"],
                               parameters["ftp_user"],
                               parameters["ftp_pass"],
                               session_factory=ftp_session_factory)
    ftp_host.use_list_a_option = False
    context.log.info('FTP connection established.')

    return ftp_host
