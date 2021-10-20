from dagster import DagsterType
from ftputil import FTPHost

FTPDagsterType = DagsterType(
    name="FTPServerType",
    type_check_fn=lambda _, value: isinstance(value, FTPHost),
)
