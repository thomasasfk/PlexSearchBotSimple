from __future__ import annotations

import os
import random

import requests
from requests.exceptions import Timeout


_TOTAL_RESULTS_TO_RETURN = 20


def search(query) -> (str, list):
    params = (
        ('apikey', os.getenv('JACKETT_API_KEY')),
        ('Query', query),
        (
            'Category[]', [
                '2000', '2010', '2020', '2030', '2040', '2045', '2050', '2060',
                '2070', '5000', '5010', '5020', '5030', '5040', '5045', '5060',
                '5070', '5080',
            ],
        ),
    )

    try:
        response = requests.get(
            os.getenv('JACKETT_URL') + os.getenv('JACKETT_URL_SEARCH'),
            params=params,
            timeout=(3, 60),
        )
    except Timeout:
        return 'Jackett timed out', None
    except ConnectionError:
        return "Jackett didn't respond", None
    except Exception:  # noqa
        return 'Something went wrong', None

    if not response.ok:
        return response.status_code, None

    json_response = response.json()
    unfiltered_results = json_response.get('Results') or []
    unique_results_by_guid = {r['Guid']: r for r in unfiltered_results}
    return None, list(unique_results_by_guid.values())


def format_and_filter_results(results: list, user_id: int, user_id_to_results: dict):
    results_by_top_seeds = sorted(
        results,
        key=lambda k: k.get('Seeders'),
        reverse=True,
    )[:_TOTAL_RESULTS_TO_RETURN]

    returned_results = []
    user_id_to_results[user_id] = {}
    for result in reversed(results_by_top_seeds):
        if result['Seeders'] < 1:
            continue

        req_id = str(random.randint(10000, 99999))
        count = 0
        while req_id in user_id_to_results[user_id] and count < 5:
            req_id = str(random.randint(10000, 99999))

            count += 1
            if count > 4:
                return 'id collision happened?...'

        user_id_to_results[user_id][req_id] = {
            'magnet': result['MagnetUri'],
            'link': result['Link'],
            'label': result['Tracker'],
            'title': result['Title'],
            'size': round((result['Size'] / 1024 / 1024 / 1024), 2),
        }

        returned_results.append(
            f"/get{req_id} - {result['Tracker']}, "
            f"Seeds: {result['Seeders']}, "
            f"Peers: {result['Peers']}, "
            f"Size: {round((result['Size'] / 1024 / 1024 / 1024), 2)}GB\n"
            f"{result['Title']}",
        )

    result_count_str = f'Results ({len(returned_results)}/{len(results)})'
    returned_results_str = '\n\n'.join(returned_results)
    return f'{result_count_str}\n\n{returned_results_str}'
