import urllib.parse
from typing import Any

import bencodepy
import pytest
import requests

from feral_services import ru_torrent


@pytest.mark.parametrize(
    "url, expected_result",
    [
        ("https://example.com?result[]=Success", "success"),
        ("https://example.com?result[]=Success&result[]=baz", "success"),
        ("https://example.com?result[]=FAILURE", "failure"),
        ("https://example.com?result[]=ERROR", "error"),
        ("https://example.com?result[]=  SUCCESS  ", "success"),  # Test whitespace handling
    ],
)
def test_format_return_url(url: str, expected_result: str) -> None:
    assert ru_torrent._format_return_url(url) == expected_result


@pytest.mark.parametrize(
    "url",
    [
        "https://example.com",
        "https://example.com?other[]=Success",
        "https://example.com?result=Success",  # Missing brackets
    ],
)
def test_format_return_url_key_error(url: str) -> None:
    with pytest.raises(KeyError):
        ru_torrent._format_return_url(url)


class MockResponse:
    def __init__(self, status_code: int, ok: bool = True, url: str | None = None) -> None:
        self.status_code = status_code
        self.ok = ok
        self.url = url


class MockTorrentInfo:
    def format_response(self) -> str:
        return "formatted_response"


@pytest.fixture
def mock_env(mocker: Any) -> None:
    mocker.patch.object(ru_torrent, "_RU_TORRENT_URL", "http://example.com")
    mocker.patch.object(ru_torrent, "_HEADERS", {"Authorization": "Basic test_token"})


@pytest.fixture
def mock_torrent_info() -> Any:
    return MockTorrentInfo()


@pytest.mark.parametrize(
    "username, label, expected_label",
    [
        ("test_user", "test_label", "test_user, test_label"),
        ("", "test_label", "test_label"),
        (None, "test_label", "test_label"),
        ("test_user", "", "test_user, "),
        ("test_user", "label with spaces", "test_user, label with spaces"),
    ],
)
def test_upload_torrent_label_formatting(
    mocker: Any, mock_env: Any, mock_torrent_info: Any, username: str, label: str, expected_label: str
) -> None:
    mocker.patch.object(ru_torrent, "_RU_TORRENT_URL", "http://example.com")
    mocker.patch.object(ru_torrent, "_HEADERS", {"Authorization": "Basic test_token"})
    mock_response = MockResponse(status_code=200, ok=True, url="http://example.com?result[]=Success")
    mocker.patch.object(requests, "post", return_value=mock_response)
    mocker.patch.object(bencodepy, "decode", return_value={b"info": {b"name": b"test.torrent"}})
    mocker.patch.object(urllib.parse, "quote", return_value="test.torrent")

    ru_torrent.upload_torrent(b"fake_torrent", label, username, mock_torrent_info)

    assert requests.post.called
    _, kwargs = requests.post.call_args
    assert kwargs["params"]["label"] == expected_label


@pytest.mark.parametrize(
    "torrent_name, quoted_name",
    [
        (b"test.torrent", "test.torrent"),
        (b"test with spaces.torrent", "test%20with%20spaces.torrent"),
        (b"test+special&chars.torrent", "test%2Bspecial%26chars.torrent"),
    ],
)
def test_upload_torrent_name_encoding(
    mocker: Any, mock_env: Any, mock_torrent_info: Any, torrent_name: str, quoted_name: str
) -> None:
    mocker.patch.object(ru_torrent, "_RU_TORRENT_URL", "http://example.com")
    mocker.patch.object(ru_torrent, "_HEADERS", {"Authorization": "Basic test_token"})
    mock_response = MockResponse(status_code=200, ok=True, url="http://example.com?result[]=Success")
    mocker.patch.object(requests, "post", return_value=mock_response)
    mocker.patch.object(bencodepy, "decode", return_value={b"info": {b"name": torrent_name}})
    mocker.patch.object(urllib.parse, "quote", side_effect=urllib.parse.quote)

    ru_torrent.upload_torrent(b"fake_torrent", "label", "user", mock_torrent_info)

    assert requests.post.called
    _, kwargs = requests.post.call_args
    assert kwargs["files"]["torrent_file"][0] == quoted_name


@pytest.mark.parametrize(
    "response_data",
    [
        {"status_code": 200, "ok": True, "url": "http://example.com?result[]=Success"},
        {"status_code": 400, "ok": False},
        {"status_code": 500, "ok": False},
        {"status_code": 200, "ok": True, "url": "http://example.com?result[]=Failure"},
    ],
)
def test_upload_torrent_responses(mocker: Any, mock_env: Any, mock_torrent_info: Any, response_data: Any) -> None:
    mocker.patch.object(ru_torrent, "_RU_TORRENT_URL", "http://example.com")
    mocker.patch.object(ru_torrent, "_HEADERS", {"Authorization": "Basic test_token"})
    mock_response = MockResponse(**response_data)
    mocker.patch.object(requests, "post", return_value=mock_response)
    mocker.patch.object(bencodepy, "decode", return_value={b"info": {b"name": b"test.torrent"}})
    mocker.patch.object(urllib.parse, "quote", return_value="test.torrent")

    result = ru_torrent.upload_torrent(b"fake_torrent", "label", "user", mock_torrent_info)

    if not mock_response.ok:
        assert result == f"Error: {mock_response.status_code}"
    elif "url" in response_data and "Success" in response_data["url"]:
        assert result == "formatted_response"
    else:
        assert "Error" in result


@pytest.mark.parametrize(
    "username, label, expected_label",
    [
        ("test_user", "test_label", "test_user, test_label"),
        ("", "test_label", "test_label"),
        (None, "test_label", "test_label"),
        ("test_user", "", "test_user, "),
        ("test_user", "label with spaces", "test_user, label with spaces"),
    ],
)
def test_upload_magnet_label_formatting(
    mocker: Any, mock_env: Any, username: str, label: str, expected_label: str
) -> None:
    mocker.patch.object(ru_torrent, "_RU_TORRENT_URL", "http://example.com")
    mocker.patch.object(ru_torrent, "_HEADERS", {"Authorization": "Basic test_token"})
    mock_response = MockResponse(status_code=200, ok=True, url="http://example.com?result[]=Success")
    mocker.patch.object(requests, "post", return_value=mock_response)

    ru_torrent.upload_magnet("magnet:?xt=test", label, username)

    assert requests.post.called
    _, kwargs = requests.post.call_args
    assert kwargs["params"]["label"] == expected_label


@pytest.mark.parametrize(
    "response_data, torrent_info, expected_result",
    [
        (
            {"status_code": 200, "ok": True, "url": "http://example.com?result[]=Success"},
            MockTorrentInfo(),
            "formatted_response",
        ),
        ({"status_code": 200, "ok": True, "url": "http://example.com?result[]=Success"}, None, "Success"),
        ({"status_code": 400, "ok": False}, MockTorrentInfo(), "Error: 400"),
        ({"status_code": 400, "ok": False}, None, "Error: 400"),
        (
            {"status_code": 200, "ok": True, "url": "http://example.com?result[]=Failure"},
            MockTorrentInfo(),
            "Error: 200",
        ),
    ],
)
def test_upload_magnet_responses(
    mocker: Any, mock_env: Any, response_data: Any, torrent_info: Any, expected_result: str
) -> None:
    mocker.patch.object(ru_torrent, "_RU_TORRENT_URL", "http://example.com")
    mocker.patch.object(ru_torrent, "_HEADERS", {"Authorization": "Basic test_token"})
    mock_response = MockResponse(**response_data)
    mocker.patch.object(requests, "post", return_value=mock_response)

    result = ru_torrent.upload_magnet("magnet:?xt=test", "label", "user", torrent_info)
    assert result == expected_result
