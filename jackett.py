import random

import requests
from requests.exceptions import Timeout


def search(query, config):
    params = (
        ('apikey', config.get('JACKETT_API_KEY')),
        ('Query', query),
        # ('Tracker[]',
        # ['eztv', 'idope', 'iptorrents', 'nyaasi', 'rarbg', 'rutracker-ru']),
        ('Category[]', [
            '2000', '2010', '2020', '2030', '2040', '2045', '2050', '2060',
            '2070', '5000', '5010', '5020', '5030', '5040', '5045', '5060',
            '5070', '5080'
        ]),
        # ('_', '1587352225849'),
    )

    try:
        response = requests.get(config.get('JACKETT_URL'), params=params, timeout=(3, 20))
    except Timeout:
        return "Jackett timed out"
    except ConnectionError:
        return "Jackett didn't respond"
    except:
        return "Something went wrong"

    if not response.ok:
        return response.status_code

    return response.json().get('Results', [])


def get_str_results(results, user_id, memory_database):
    return_string = ''
    sort_by_seeders = sorted(results, key=lambda k: k['Seeders'], reverse=True)

    result_counter = 0
    memory_database[user_id] = {}
    for r in reversed(sort_by_seeders[:25]):

        req_id = random.randint(10000, 99999)
        count = 0
        while req_id in memory_database[user_id] and count < 5:
            req_id = random.randint(10000, 99999)

            count += 1
            if count > 4:
                return "1 in a mirrion"

        if r['Seeders'] > 0:
            memory_database[user_id][str(req_id)] = {
                'magnet': r['MagnetUri'],
                'link': r['Link'],
                'label': r['Tracker'],
                'title': r['Title'],
                'size': str(round((r['Size'] / 1024 / 1024 / 1024), 2)),
            }

            result_counter += 1
            return_string += '/get{} - {}, Seeds: {}, Peers: {}, Size: {}GB'.format(
                str(req_id), r['Tracker'], str(r['Seeders']), str(r['Peers']),
                str(round((r['Size'] / 1024 / 1024 / 1024), 2)))
            return_string += '\n{}\n\n'.format(r['Title'])

    return "Results ({}/{})\n\n{}".format(
        str(result_counter), str(len(results)), return_string)
