import datetime
from asyncio.log import logger


def set_harvesting_interval(repo, **kwargs):
    if (
        "params" in kwargs
        and "start_date" in kwargs["params"]
        and "until_date" in kwargs["params"]
    ):
        return {
            "start_date": kwargs["params"]["start_date"],
            "until_date": kwargs["params"]["until_date"],
        }
    start_date = repo.find_the_last_uploaded_file_date()
    until_date = datetime.date.today().strftime("%Y-%m-%d")
    return {
        "start_date": (start_date or until_date),
        "until_date": until_date,
    }


def construct_license(url, license_type, version):
    if url and license_type and version:
        return {"url": url, "license": f"CC-{license_type}-{version}"}
    logger.error("Licence is not given, or missing arguments.")
