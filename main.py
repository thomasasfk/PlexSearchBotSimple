from __future__ import annotations

import contextlib
import json
import os
import threading

import requests
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import Application
from telegram.ext import CommandHandler
from telegram.ext import MessageHandler
from telegram.ext.filters import COMMAND

from feral_services import jackett
from feral_services import ru_torrent
from feral_services.instance import execute_command
load_dotenv()

_MEMORY_DATABASE = {}
_USERS_FILE = 'users.json'
_USERS = set(json.load(open(_USERS_FILE)))
_ADMINS = set(os.getenv('ADMINS').split(','))
_LINUX_DIR_SIZE = 0


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


def admin_required(func):
    async def wrapper(update, context):
        if str(update.effective_user.id) not in _ADMINS:
            await update.message.reply_text('Bad, no admin')
            return
        return await func(update, context)

    return wrapper


def get_home_size(start_new_thread=True):
    global _LINUX_DIR_SIZE

    size = 0
    home = os.path.expanduser('~')
    for dirpath, _, filenames in os.walk(home):
        for file in filenames:
            file_path = os.path.join(dirpath, file)
            size += os.path.getsize(file_path)

    _LINUX_DIR_SIZE = size
    if start_new_thread:
        threading.Timer(3600, get_home_size).start()


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
async def spaceforce(_update: Update, _context):
    get_home_size(start_new_thread=False)
    await space(_update, _context)


@auth_required
async def space(_update: Update, _context):
    await _update.message.reply_text(
        f'Home dir size: {_LINUX_DIR_SIZE / 1024 / 1024 / 1024:.2f}/1000 GB',
    )


@auth_required
async def search(update: Update, _context):
    _, term = update.message.text.split('/search', 1)
    error, results = jackett.search(term)
    if results:
        returned_results_str = jackett.format_and_filter_results(
            results, update.effective_user.id,
            _MEMORY_DATABASE,
        )
        await update.message.reply_text(returned_results_str)
    await update.message.reply_text(error)


@auth_required
async def download(update: Update, _context):
    _, magnet = update.message.text.split('/download', 1)
    username = update.effective_user.username or update.effective_user.first_name
    magnet_upload_result = ru_torrent.upload_magnet(
        magnet,
        '/download',
        username,
    )
    await update.message.reply_text(magnet_upload_result)


@auth_required
async def get(update: Update, _context):
    if not update.message.text.startswith('/get'):
        return

    if update.effective_user.id not in _USERS:
        await update.message.reply_text('Authorise please')
        return

    users_data = _MEMORY_DATABASE.get(update.effective_user.id)
    if not users_data:
        await update.message.reply_text('Not a valid item')
        return

    _, get_id = update.message.text.split('/get', 1)
    result = users_data.get(get_id)
    if not result:
        await update.message.reply_text('Not a valid item')
        return

    username = update.effective_user.username or update.effective_user.first_name
    if magnet := result.get('magnet'):
        magnet_upload_result = ru_torrent.upload_magnet(
            magnet,
            result['label'],
            username,
        )
        await update.message.reply_text(magnet_upload_result)
        return

    elif link := result.get('link'):
        url_response = requests.get(link, allow_redirects=False)
        if not url_response.ok:
            await update.message.reply_text(
                'Something went wrong downloading torrent file. The url was: '
                f'{link}',
            )
            return

        with contextlib.suppress(Exception):
            if url_response.status_code == 302:
                magnet_upload_result = ru_torrent.upload_magnet(
                    url_response.headers['Location'],
                    result['label'],
                    username,
                )
                await update.message.reply_text(magnet_upload_result)
                return

            torrent_upload_result = ru_torrent.upload_torrent(
                url_response.content,
                result['label'],
                username,
            )
            await update.message.reply_text(torrent_upload_result)
            return

    await update.message.reply_text('Something went wrong')


@admin_required
async def sh(update: Update, _context):
    _, command = update.message.text.split('/sh', 1)
    output = execute_command(command)
    await update.message.reply_text(output)


def main() -> None:
    application = Application \
        .builder() \
        .token(os.getenv('TELEGRAM_TOKEN')) \
        .build()
    application.add_handlers(
        [
            CommandHandler('spaceforce', spaceforce),
            CommandHandler('space', space),
            CommandHandler('auth', auth),
            CommandHandler('search', search),
            CommandHandler('download', download),
            CommandHandler('sh', sh),
            MessageHandler(COMMAND, get),
        ],
    )

    print('Getting home size!')
    get_home_size()

    print('Starting polling!')
    application.run_polling()


if __name__ == '__main__':
    main()
