from __future__ import annotations

import urllib.parse

import bencodepy
import pytest
import requests

from feral_services import ru_torrent


@pytest.mark.parametrize(
    'url, expected_result', [
        ('https://example.com?result[]=Success', 'Success'),
        ('https://example.com?result[]=Success&result[]=baz', 'Success'),
    ],
)
def test_format_return_url(url, expected_result):
    assert ru_torrent._format_return_url(url) == expected_result


def test_format_return_url_key_error():
    with pytest.raises(KeyError):
        ru_torrent._format_return_url('https://example.com')


class MockResponse:
    def __init__(self, status_code, ok=True, url=None):
        self.status_code = status_code
        self.ok = ok
        self.url = url


@pytest.mark.parametrize(
    'upload_function', [
        ru_torrent.upload_torrent,
        ru_torrent.upload_magnet,
    ],
)
@pytest.mark.parametrize(
    'response', [
        MockResponse(
            status_code=200,
            url='http://example.com?result[]=Success',
        ),
        MockResponse(status_code=400, ok=False),
    ],
)
def test_upload_function(mocker, upload_function, response):
    mocker.patch.object(requests, 'post', return_value=response)
    mocker.patch.object(bencodepy, 'decode')
    mocker.patch.object(urllib.parse, 'quote')

    result = upload_function('file_or_link', 'my_label')
    if response.ok:
        assert result == ru_torrent._format_return_url(response.url)
    else:
        assert result == f'Error: {response.status_code}'
