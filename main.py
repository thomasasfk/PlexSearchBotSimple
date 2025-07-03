import json
import os
import threading
from collections.abc import Callable
from typing import Any

import requests
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes, MessageHandler
from telegram.ext.filters import COMMAND

from feral_services import jackett, ru_torrent
from feral_services.jackett import TorrentInfo

load_dotenv()

_RESULTS: dict[int, dict[str, TorrentInfo]] = {}
_LAST_RESULT_DICT: dict[int, int] = {}
_USERS_FILE = "users.json"
_USERS: set[int] = set(json.load(open(_USERS_FILE)))
_ADMINS: set[str] = set((os.getenv("ADMINS") or "").split(","))
_LINUX_DIR_SIZE = 0


def save_user(user_id: int) -> None:
    _USERS.add(user_id)
    json.dump(list(_USERS), open(_USERS_FILE, "w"))


def auth_required(
    func: Callable[[Update, ContextTypes.DEFAULT_TYPE], Any],
) -> Callable[[Update, ContextTypes.DEFAULT_TYPE], Any]:
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE) -> Any:
        if not update.effective_user or not update.message:
            return
        if update.effective_user.id not in _USERS:
            await update.message.reply_text("Authorise pls")
            return
        return await func(update, context)

    return wrapper


def admin_required(
    func: Callable[[Update, ContextTypes.DEFAULT_TYPE], Any],
) -> Callable[[Update, ContextTypes.DEFAULT_TYPE], Any]:
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE) -> Any:
        if not update.effective_user or not update.message:
            return
        if str(update.effective_user.id) not in _ADMINS:
            await update.message.reply_text("Bad, no admin")
            return
        return await func(update, context)

    return wrapper


def get_home_size(start_new_thread: bool = True) -> None:
    global _LINUX_DIR_SIZE

    size = 0
    home = os.path.expanduser("~")
    for dirpath, _, filenames in os.walk(home):
        for file in filenames:
            file_path = os.path.join(dirpath, file)
            size += os.path.getsize(file_path)

    _LINUX_DIR_SIZE = size
    if start_new_thread:
        threading.Timer(3600, get_home_size).start()


async def auth(update: Update, _context: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.effective_user or not update.message:
        return

    if update.effective_user.id in _USERS:
        await update.message.reply_text("Already authorized")
        return

    password = os.getenv("PASSWORD")
    if password and password in (update.message.text or ""):
        save_user(update.effective_user.id)
        await update.message.reply_text("Authorized")
        return

    await update.message.reply_text("Wrong password")


@auth_required
async def spaceforce(_update: Update, _context: ContextTypes.DEFAULT_TYPE) -> None:
    get_home_size(start_new_thread=False)
    await space(_update, _context)


@auth_required
async def space(_update: Update, _context: ContextTypes.DEFAULT_TYPE) -> None:
    if not _update.message:
        return
    await _update.message.reply_text(
        f"Home dir size: {_LINUX_DIR_SIZE / 1024 / 1024 / 1024:.2f}/1000 GB",
    )


@auth_required
async def search(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.message or not update.message.text or not update.effective_user or not update.effective_chat:
        return

    _, term = update.message.text.split("/search", 1)
    error, results = jackett.search(term)
    if error or not results:
        await update.message.reply_text(error or "No results found")
        return

    user_id = update.effective_user.id
    if prior_search_msg_id := _LAST_RESULT_DICT.get(user_id):
        await context.bot.edit_message_text(
            chat_id=update.effective_chat.id,
            message_id=prior_search_msg_id,
            text=r"Previous search results have expired\. "
            r"Use the latest search results below\.",
            parse_mode="MarkdownV2",
        )

    returned_results_str = jackett.format_and_filter_results(
        results,
        user_id,
        _RESULTS,
    )
    message = await update.message.reply_text(returned_results_str)
    _LAST_RESULT_DICT[user_id] = message.message_id


@auth_required
async def download(update: Update, _context: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.message or not update.message.text or not update.effective_user:
        return

    _, magnet = update.message.text.split("/download", 1)
    username = update.effective_user.username or update.effective_user.first_name or "Unknown"
    magnet_upload_result = ru_torrent.upload_magnet(
        magnet,
        "/download",
        username,
    )
    await update.message.reply_text(magnet_upload_result)


@auth_required
async def get(update: Update, _context: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.message or not update.message.text or not update.effective_user:
        return

    if not update.message.text.startswith("/get"):
        return

    if update.effective_user.id not in _USERS:
        await update.message.reply_text("Authorise please")
        return

    users_data = _RESULTS.get(update.effective_user.id)
    if not users_data:
        await update.message.reply_text("Not a valid item")
        return

    _, get_id = update.message.text.split("/get", 1)
    result = users_data.get(get_id)
    if not result:
        await update.message.reply_text("Not a valid item")
        return

    username = update.effective_user.username or update.effective_user.first_name or "Unknown"
    if magnet := result.magnet:
        magnet_upload_result = ru_torrent.upload_magnet(magnet, result.source, username, result)
        await update.message.reply_text(magnet_upload_result)
        return

    elif link := result.link:
        url_response = requests.get(link, allow_redirects=False)
        if not url_response.ok:
            await update.message.reply_text(
                f"Something went wrong downloading torrent file. The url was: {link}",
            )
            return

        try:
            if url_response.status_code == 302:
                magnet_upload_result = ru_torrent.upload_magnet(
                    url_response.headers["Location"], result.source, username, result
                )
                await update.message.reply_text(magnet_upload_result)
                return

            torrent_upload_result = ru_torrent.upload_torrent(url_response.content, result.source, username, result)
            await update.message.reply_text(torrent_upload_result)
            return
        except Exception as e:
            print(e)

    await update.message.reply_text("Something went wrong")


def main() -> None:
    token = os.getenv("TELEGRAM_TOKEN")
    if not token:
        raise ValueError("TELEGRAM_TOKEN environment variable is required")
    application = Application.builder().token(token).build()
    application.add_handlers(
        [
            CommandHandler("spaceforce", spaceforce),
            CommandHandler("space", space),
            CommandHandler("auth", auth),
            CommandHandler("search", search),
            CommandHandler("download", download),
            MessageHandler(COMMAND, get),
        ],
    )

    print("Getting home size!")
    get_home_size()

    print("Starting polling!")
    application.run_polling()


if __name__ == "__main__":
    main()
