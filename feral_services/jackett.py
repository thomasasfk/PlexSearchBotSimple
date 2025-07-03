import os
import random
import traceback
from dataclasses import dataclass
from typing import Any

import requests
from requests.exceptions import ConnectionError, Timeout

_TOTAL_RESULTS_TO_RETURN = 20


@dataclass
class TorrentInfo:
    name: str
    size: str
    seeds: int
    peers: int
    source: str
    magnet: str
    link: str

    def format_response(self, req_id: str | None = None) -> str:
        prefix = f"/get{req_id} - " if req_id else "Success - "
        return f"{prefix}{self.name}\n└─ {self.source} | Seeds: {self.seeds:,} | Size: {self.size}"


def search(query: str) -> tuple[str | None, list[dict[str, Any]] | None]:
    params = (
        ("apikey", os.getenv("JACKETT_API_KEY")),
        ("Query", query),
        (
            "Category[]",
            [
                "2000",
                "2010",
                "2020",
                "2030",
                "2040",
                "2045",
                "2050",
                "2060",
                "2070",
                "5000",
                "5010",
                "5020",
                "5030",
                "5040",
                "5045",
                "5060",
                "5070",
                "5080",
            ],
        ),
    )

    try:
        jackett_url = os.getenv("JACKETT_URL")
        jackett_search = os.getenv("JACKETT_URL_SEARCH")
        if not jackett_url or not jackett_search:
            return "Missing JACKETT_URL or JACKETT_URL_SEARCH environment variables", None

        response = requests.get(
            jackett_url + jackett_search,
            params=params,
            timeout=(3, 60),
        )
    except Timeout:
        return "Jackett timed out", None
    except ConnectionError:
        return "Jackett didn't respond", None
    except Exception as e:
        error_msg = f"Something went wrong: {type(e).__name__}: {e!s}"
        stack_trace = traceback.format_exc()
        return f"{error_msg}\n\nStack trace:\n{stack_trace}", None

    if not response.ok:
        return str(response.status_code or 500), None

    json_response = response.json()
    unfiltered_results = json_response.get("Results") or []
    unique_results_by_guid = {r["Guid"]: r for r in unfiltered_results}
    return None, list(unique_results_by_guid.values())


def format_and_filter_results(
    results: list[dict[str, Any]], user_id: int, user_id_to_results: dict[int, dict[str, TorrentInfo]]
) -> str:
    results_by_top_seeds = sorted(
        results,
        key=lambda k: k.get("Seeders", 0),
        reverse=True,
    )[:_TOTAL_RESULTS_TO_RETURN]

    returned_results = []
    user_id_to_results[user_id] = {}

    for result in reversed(results_by_top_seeds):
        if result["Seeders"] < 1:
            continue

        req_id = str(random.randint(10000, 99999))
        count = 0
        while req_id in user_id_to_results[user_id] and count < 5:
            req_id = str(random.randint(10000, 99999))
            count += 1
            if count > 4:
                return "id collision happened?..."

        torrent_info = TorrentInfo(
            name=result["Title"],
            size=f"{round((result['Size'] / 1024 / 1024 / 1024), 2)} GB",
            seeds=result["Seeders"],
            peers=result["Peers"],
            source=result["Tracker"],
            magnet=result["MagnetUri"],
            link=result["Link"],
        )

        user_id_to_results[user_id][req_id] = torrent_info
        returned_results.append(torrent_info.format_response(req_id))

    result_count_str = f"Results ({len(returned_results)}/{len(results)})"
    returned_results_str = "\n\n".join(returned_results)
    return f"{result_count_str}\n\n{returned_results_str}"
