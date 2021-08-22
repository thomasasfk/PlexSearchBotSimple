import requests
import bencodepy
import urllib


def upload_torrent(torrent_file, label, config):
    metadata = bencodepy.decode(torrent_file)
    file_name = urllib.parse.quote(metadata[b'info'][b'name'].decode())

    params = {'label': label}
    headers = {'Authorization': f'Basic {config.get("RU_TORRENT_TOKEN")}'}
    files = {'torrent_file': (file_name, torrent_file)}

    response = requests.post(
        config.get("RU_TORRENT_URL"),
        headers=headers,
        files=files,
        params=params)

    if response.status_code == 200:
        return response.url[76:].split("&")[0]

    return 'Error: {}'.format(response.status_code)


def upload_magnet(magnet_link, label, config):
    data = {'url': magnet_link}
    headers = {'Authorization': f'Basic {config.get("RU_TORRENT_TOKEN")}'}
    params = {'label': label}

    response = requests.post(
        config.get("RU_TORRENT_URL"), headers=headers, params=params, data=data)
    if response.ok:
        return response.url[76:].split('&')[0][1:]

    return response.status_code
