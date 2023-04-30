from __future__ import annotations

import os
import urllib.parse

import bencodepy
import requests
from dotenv import load_dotenv
load_dotenv()


_HEADERS = {'Authorization': f'Basic {os.getenv("RU_TORRENT_TOKEN")}'}
_RU_TORRENT_URL = os.getenv('RU_TORRENT_URL')


def _format_return_url(url):
    parsed_url = urllib.parse.urlparse(url)
    query_params = urllib.parse.parse_qs(parsed_url.query)
    return query_params['result[]'][0]


def upload_torrent(torrent_file, label):
    metadata = bencodepy.decode(torrent_file)
    file_name = urllib.parse.quote(
        metadata[b'info'][b'name'].decode(),  # noqa
    )

    response = requests.post(
        _RU_TORRENT_URL,
        headers=_HEADERS,
        files={'torrent_file': (file_name, torrent_file)},
        params={'label': label},
    )

    if response.ok:
        return _format_return_url(response.url)
    return f'Error: {response.status_code}'


def upload_magnet(magnet_link, label):
    response = requests.post(
        _RU_TORRENT_URL,
        headers=_HEADERS,
        params={'label': label},
        data={'url': magnet_link},
    )

    if response.ok:
        return _format_return_url(response.url)
    return f'Error: {response.status_code}'
