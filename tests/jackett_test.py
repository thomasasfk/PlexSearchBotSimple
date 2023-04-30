from __future__ import annotations

import pytest
from requests.exceptions import Timeout

from feral_services import jackett

_SHAWSHANK_RESULTS = [  # noqa
    {
        'FirstSeen': '0001-01-01T00:00:00', 'Tracker': '1337x',
        'TrackerId': '1337x', 'CategoryDesc': 'Movies/HD',
        'BlackholeLink': None,
        'Title': 'The Shawshank Redemption 1994 REMASTERED 1080p BluRay H264 AAC R4RBG TGx',  # noqa
        'Guid': 'https://example.com',
        'Link': 'https://example.com',
        'Details': 'https://example.com',
        'PublishDate': '2023-04-10T05:00:00',
        'Category': [2040, 100042], 'Size': 2989297152,
        'Files': None, 'Grabs': None, 'Description': None,
        'RageID': None, 'TVDBId': None, 'Imdb': None,
        'TMDb': None, 'Author': None, 'BookTitle': None,
        'Seeders': 84, 'Peers': 15, 'Poster': None,
        'InfoHash': None, 'MagnetUri': None,
        'MinimumRatio': None, 'MinimumSeedTime': None,
        'DownloadVolumeFactor': 0.0, 'UploadV olumeFactor': 1.0,
        'Gain': 233.85599327087402,
    },
    {
        'FirstSeen': '0001-01-01T00:00:00',
        'Tracker': 'IPTorrents', 'TrackerId': 'iptorrents',
        'CategoryDesc': 'Movies/BluRay', 'BlackholeLink': None,
        'Title': 'The Shawshank Redemption 1994 REMASTERED 1080p BluRay H264 AAC-LAMA',  # noqa
        'Guid': 'https://example.com',
        'Link': 'https://example.com',
        'Details': 'https://example.com',
        'PublishDate': '2023-04-09T21:55:13.9457906+00:00',
        'Catego ry': [2050, 100048], 'Size': 2909840384,
        'Files': None, 'Grabs': 163,
        'Description': 'Tags: 9.3 1994 Drama 1080p Uploaded by: Lama',
        'RageID': None, 'TVDBId': None, 'Imdb': None,
        'TMDb': None, 'Author': None, 'BookTitle': None,
        'Seeders': 42, 'Peers': 0, 'Poster': None,
        'InfoHash': None, 'MagnetUri': None,
        'MinimumRatio': 1.0, 'MinimumSeedTime': 1209600,
        'DownloadVolumeFactor': 1.0, 'UploadVolumeFac tor': 1.0,
        'Gain': 113.82000160217285,
    },
]


@pytest.mark.parametrize(
    'query, expected_output',
    [
        ('The Shawshank Redemption', _SHAWSHANK_RESULTS),
        ('Not a valid query', []),
    ],
)
def test_search_valid_query(query, expected_output, mocker):
    mocker.patch('requests.get').return_value.ok = True
    mocker.patch('requests.get').return_value.json.return_value = {
        'Results': expected_output,
    }

    output = jackett.search(query)

    assert output == expected_output


@pytest.mark.parametrize(
    'query, exception, error_message',
    [
        ('The Godfather', Timeout, 'Jackett timed out'),
        ('The Dark Knight', ConnectionError, "Jackett didn't respond"),
        ('The Lord of the Rings', Exception, 'Something went wrong'),
    ],
)
def test_search_invalid_query(query, exception, error_message, mocker):
    mocker.patch('requests.get').side_effect = exception

    output = jackett.search(query)

    assert output == error_message


def test_format_and_filter_results(mocker):
    mocker.patch('random.randint', side_effect=[11111, 22222])

    user_id = 12345
    memory_database = {}
    results = _SHAWSHANK_RESULTS
    formatted_results = jackett.format_and_filter_results(
        results, user_id, memory_database,
    )

    assert isinstance(formatted_results, str)

    expected_result_count_str = 'Results (2/2)'
    expected_returned_results_str = (
        '/get11111 - IPTorrents, Seeds: 42, Peers: 0, Size: 2.71GB\n'
        'The Shawshank Redemption 1994 REMASTERED 1080p BluRay H264 AAC-LAMA\n\n'  # noqa
        '/get22222 - 1337x, Seeds: 84, Peers: 15, Size: 2.78GB\n'
        'The Shawshank Redemption 1994 REMASTERED 1080p BluRay H264 AAC R4RBG TGx'  # noqa
    )
    assert formatted_results.startswith(expected_result_count_str)
    assert expected_returned_results_str in formatted_results

    assert len(memory_database) == 1
    assert isinstance(memory_database[user_id], dict)
    assert len(memory_database[user_id]) == 2
    for req_id, values in memory_database[user_id].items():
        assert isinstance(req_id, str)
        assert isinstance(values, dict)
        assert set(values.keys()) == {
            'magnet', 'link', 'label', 'title', 'size',
        }
