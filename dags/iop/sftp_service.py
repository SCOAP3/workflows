import os

from common.sftp_service import SFTPService


class IOPSFTPService(SFTPService):
    def __init__(self):
        super().__init__(
            host=os.getenv("IOP_FTP_HOST", "localhost"),
            username=os.getenv("IOP_FTP_USERNAME", "airflow"),
            password=None,
            port=int(os.getenv("IOP_FTP_PORT", "2222")),
            dir=os.getenv("IOP_FTP_DIR", "upload/iop"),
            private_key_content=os.getenv("IOP_FTP_SSH_PRIVATE_KEY"),
        )


class IOPSFTPServiceNew(SFTPService):
    def __init__(self):
        super().__init__(
            host=os.getenv("IOP_NEW_FTP_HOST", "localhost"),
            username=os.getenv("IOP_NEW_FTP_USERNAME", "airflow"),
            password=None,
            port=int(os.getenv("IOP_NEW_FTP_PORT", "2222")),
            dir=os.getenv("IOP_NEW_FTP_DIR", "scoapfeed"),
            private_key_content=os.getenv("IOP_NEW_FTP_SSH_PRIVATE_KEY"),
        )
