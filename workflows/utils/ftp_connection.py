import ftplib
from ftputil import session


ftp_session_factory = session.session_factory(
    base_class=ftplib.FTP,
    port=21,
    encrypt_data_channel=False,
    use_passive_mode=True
)
