from __future__ import annotations

import contextlib
import json
import os

import requests
from telegram import Update
from telegram.ext import Application
from telegram.ext import CommandHandler
from telegram.ext import MessageHandler
from telegram.ext.filters import COMMAND

from feral_services import jackett
from feral_services import ru_torrent

_MEMORY_DATABASE = {}
_USERS_FILE = 'users.json'
_USERS = set(json.load(open(_USERS_FILE)))


def save_user(user_id):
    _USERS.add(user_id)
    json.dump(list(_USERS), open(_USERS_FILE, 'w'))


def auth_required(func):
    async def wrapper(update, context):
        if update.effective_user.id not in _USERS:
            await update.message.reply_text('Authorise pls')
            return
        return await func(update, context)

    return wrapper


async def auth(update: Update, _context):
    if update.effective_user.id in _USERS:
        await update.message.reply_text('Already authorized')
        return

    if os.getenv('PASSWORD') in update.message.text:
        save_user(update.effective_user.id)
        await update.message.reply_text('Authorized')
        return

    await update.message.reply_text('Wrong password')


@auth_required
async def search(update: Update, _context):
    _, term = update.message.text.split('/search', 1)
    results = jackett.search(term)
    returned_results_str = jackett.format_and_filter_results(
        results, update.effective_user.id,
        _MEMORY_DATABASE,
    ) if results else 'No results found'
    await update.message.reply_text(returned_results_str)


@auth_required
async def download(update: Update, _context):
    _, magnet = update.message.text.split('/download', 1)
    magnet_upload_result = ru_torrent.upload_magnet(magnet, 'Manual upload')
    await update.message.reply_text(magnet_upload_result)


@auth_required
async def get(update: Update, _context):
    if not update.message.text.startswith('/get'):
        return

    if update.effective_user.id not in _USERS:
        await update.message.reply_text('Authorise please')
        return

    _, get_id = update.message.text.split('/get', 1)
    users_data = _MEMORY_DATABASE.get(update.effective_user.id)
    if not users_data:
        await update.message.reply_text('No results found')
        return

    result = users_data.get(get_id)
    if not result:
        await update.message.reply_text('No results found')
        return

    if result.get('magnet'):
        magnet_upload_result = ru_torrent.upload_magnet(
            result['magnet'],
            result['label'],
        )
        await update.message.reply_text(magnet_upload_result)
        return

    elif result.get('link'):
        url_response = requests.get(result['link'], allow_redirects=False)
        if not url_response.ok:
            await update.message.reply_text(
                'Something went wrong downloading torrent file. The url was: '
                f'{result["link"]}',
            )
            return

        with contextlib.suppress(Exception):
            if url_response.status_code == 302:
                magnet_upload_result = ru_torrent.upload_magnet(
                    url_response.headers['Location'], result['label'],
                )
                await update.message.reply_text(magnet_upload_result)
                return

            print('torrent file!!')
            torrent_upload_result = ru_torrent.upload_torrent(
                url_response.content, result['label'],
            )
            await update.message.reply_text(torrent_upload_result)
            return

    await update.message.reply_text('Something went wrong')


def main() -> None:
    application = Application \
        .builder() \
        .token(os.getenv('TELEGRAM_TOKEN')) \
        .build()
    application.add_handlers([
        CommandHandler('auth', auth),
        CommandHandler('search', search),
        CommandHandler('download', download),
        MessageHandler(COMMAND, get),
    ])
    print('Starting polling!')
    application.run_polling()


if __name__ == '__main__':
    main()
