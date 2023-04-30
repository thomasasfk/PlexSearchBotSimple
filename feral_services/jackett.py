from __future__ import annotations

import os
import random

import requests
from dotenv import load_dotenv
from requests.exceptions import Timeout
load_dotenv()


def search(query):
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
            os.getenv('JACKETT_URL'),
            params=params,
            timeout=(3, 60),
        )
    except Timeout:
        return 'Jackett timed out'
    except ConnectionError:
        return "Jackett didn't respond"
    except Exception:  # noqa
        return 'Something went wrong'

    if not response.ok:
        return response.status_code

    json_response = response.json()
    return json_response.get('Results') or []


def format_and_filter_results(results, user_id, memory_database):
    results_by_top_seeds = sorted(
        results,
        key=lambda k: k.get('Seeders'),
        reverse=True,
    )[:25]

    returned_results = []
    memory_database[user_id] = {}
    for result in reversed(results_by_top_seeds):
        if result['Seeders'] < 1:
            continue

        req_id = str(random.randint(10000, 99999))
        count = 0
        while req_id in memory_database[user_id] and count < 5:
            req_id = str(random.randint(10000, 99999))

            count += 1
            if count > 4:
                return 'id collision happened?...'

        memory_database[user_id][req_id] = {
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
