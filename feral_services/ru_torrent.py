from __future__ import annotations
from dotenv import load_dotenv

import os
import urllib.parse

import bencodepy
import requests

from feral_services.jackett import TorrentInfo

load_dotenv()


_HEADERS = {'Authorization': f'Basic {os.getenv("RU_TORRENT_TOKEN")}'}
_RU_TORRENT_URL = os.getenv('RU_TORRENT_URL')


def _format_return_url(url):
    parsed_url = urllib.parse.urlparse(url)
    query_params = urllib.parse.parse_qs(parsed_url.query)
    return query_params['result[]'][0].strip().casefold()


def upload_torrent(torrent_file, label: str, username: str, torrent_info: TorrentInfo):
    metadata = bencodepy.decode(torrent_file)
    file_name = urllib.parse.quote(
        metadata[b'info'][b'name'].decode(),  # noqa
    )

    if username:
        label = f'{username}, {label}'

    response = requests.post(
        _RU_TORRENT_URL,
        headers=_HEADERS,
        files={'torrent_file': (file_name, torrent_file)},
        params={'label': label},
    )

    if response.ok:
        status = _format_return_url(response.url)
        if status == "success":
            return torrent_info.format_response()
    return f'Error: {response.status_code}'


def upload_magnet(magnet_link: str, label: str, username: str, torrent_info: TorrentInfo | None = None):
    if username:
        label = f'{username}, {label}'

    response = requests.post(
        _RU_TORRENT_URL,
        headers=_HEADERS,
        data={'url': magnet_link},
        params={'label': label},
    )

    if response.ok:
        status = _format_return_url(response.url)
        if torrent_info:
            if status == "success":
                return torrent_info.format_response()
        else:
            return status.capitalize()
    return f'Error: {response.status_code}'