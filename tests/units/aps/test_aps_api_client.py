from unittest import mock

from aps.aps_api_client import APSApiClient
from aps.aps_params import APSParams


def mocked_response(*args, **kwrgs):
    mocked_response = mock.Mock(autospec=True)
    mocked_response.status_code = 200
    mocked_response.url = args[0]
    mocked_response.content = '{"data":[{"abstract":{"value":"<p>We propose and theoretically analyze</p>"}}]}'
    mocked_response.json = mock.MagicMock(
        return_value={
            "data": [
                {"abstract": {"value": "<p>We propose and theoretically analyze</p>"}}
            ]
        }
    )
    return mocked_response


@mock.patch("common.request.requests.get", side_effect=mocked_response)
def test_get_articles_metadata(mocked_response):
    parameters = APSParams(
        from_date="2021-01-01",
        until_date="2021-01-02",
    ).get_params()
    aps_api_client = APSApiClient()
    metadata = aps_api_client.get_articles_metadata(parameters=parameters)
    assert metadata == {
        "data": [{"abstract": {"value": "<p>We propose and theoretically analyze</p>"}}]
    }


def mocked_single_article_response(*args, **kwrgs):
    mocked_response = mock.Mock()
    mocked_response.status_code = 200
    mocked_response.url = args[0]
    mocked_response.content = (
        '{"data":{"identifiers":{"doi":"10.1103/PhysRevX.6.041064"}}}'
    )
    mocked_response.json = mock.MagicMock(
        return_value={"data": {"identifiers": {"doi": "10.1103/PhysRevX.6.041064"}}}
    )
    return mocked_response


@mock.patch("common.request.requests.get", side_effect=mocked_single_article_response)
def test_get_articles_metadata_single_doi(mocked_get):
    aps_api_client = APSApiClient()
    metadata = aps_api_client.get_articles_metadata(
        parameters=None, doi="10.1103/PhysRevX.6.041064"
    )
    assert metadata == {"data": [{"identifiers": {"doi": "10.1103/PhysRevX.6.041064"}}]}
    requested_url = mocked_get.call_args[0][0]
    assert "10.1103%2FPhysRevX.6.041064" in requested_url


def mocked_empty_response(*args, **kwrgs):
    mocked_response = mock.Mock()
    mocked_response.status_code = 200
    mocked_response.url = args[0]
    mocked_response.content = '{"data":[]}'
    mocked_response.json = mock.MagicMock(return_value={"data": []})
    return mocked_response


@mock.patch("common.request.requests.get", side_effect=mocked_empty_response)
def test_get_articles_metadata_empty(mocked_response):
    parameters = APSParams(
        from_date="2021-01-01",
        until_date="2021-01-02",
    ).get_params()
    aps_api_client = APSApiClient()
    metadata = aps_api_client.get_articles_metadata(parameters=parameters)
    assert metadata is None
