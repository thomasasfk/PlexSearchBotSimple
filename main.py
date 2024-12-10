from __future__ import annotations

import os

import requests
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import Application
from telegram.ext import CommandHandler
from telegram.ext import MessageHandler
from telegram.ext.filters import COMMAND

from feral_services import jackett
from feral_services import ru_torrent
from feral_services.jackett import TorrentInfo

load_dotenv()

_RESULTS = {}
_LAST_RESULT_DICT = {}
_ADMINS = set(os.getenv("ADMINS").split(","))


def admin_required(func):
    async def wrapper(update, context):
        if str(update.effective_user.id) in _ADMINS:
            return await func(update, context)
    return wrapper

@admin_required
async def search(update: Update, context):
    _, term = update.message.text.split("/search", 1)
    error, results = jackett.search(term)
    if error:
        await update.message.reply_text("No results found")
        return
    elif not results:
        await update.message.reply_text(error)
        return

    user_id = update.effective_user.id
    if prior_search_msg_id := _LAST_RESULT_DICT.get(user_id):
        await context.bot.edit_message_text(
            chat_id=update.effective_chat.id,
            message_id=prior_search_msg_id,
            text=f"Previous search results have expired\. "
                 f"Use the latest search results below\.",
            parse_mode="MarkdownV2"
        )

    returned_results_str = jackett.format_and_filter_results(
        results, user_id, _RESULTS,
    )
    message = await update.message.reply_text(returned_results_str)
    _LAST_RESULT_DICT[user_id] = message.message_id


@admin_required
async def download(update: Update, _context):
    _, magnet = update.message.text.split("/download", 1)
    username = update.effective_user.username or update.effective_user.first_name
    magnet_upload_result = ru_torrent.upload_magnet(
        magnet,
        "/download",
        username,
    )
    await update.message.reply_text(magnet_upload_result)


@admin_required
async def get(update: Update, _context):
    if not update.message:
        return

    if not update.message.text.startswith("/get"):
        return

    users_data = _RESULTS.get(update.effective_user.id)
    if not users_data:
        await update.message.reply_text("Not a valid item")
        return

    _, get_id = update.message.text.split("/get", 1)
    result: TorrentInfo = users_data.get(get_id)
    if not result:
        await update.message.reply_text("Not a valid item")
        return

    username = update.effective_user.username or update.effective_user.first_name
    if magnet := result.magnet:
        magnet_upload_result = ru_torrent.upload_magnet(
            magnet,
            result.source,
            username,
            result
        )
        await update.message.reply_text(magnet_upload_result)
        return

    elif link := result.link:
        url_response = requests.get(link, allow_redirects=False)
        if not url_response.ok:
            await update.message.reply_text(
                "Something went wrong downloading torrent file. The url was: "
                f"{link}",
            )
            return

        try:
            if url_response.status_code == 302:
                magnet_upload_result = ru_torrent.upload_magnet(
                    url_response.headers["Location"],
                    result.source,
                    username,
                    result
                )
                await update.message.reply_text(magnet_upload_result)
                return

            torrent_upload_result = ru_torrent.upload_torrent(
                url_response.content,
                result.source,
                username,
                result
            )
            await update.message.reply_text(torrent_upload_result)
            return
        except Exception as e:
            print(e)

    await update.message.reply_text("Something went wrong")

def main() -> None:
    application = Application \
        .builder() \
        .token(os.getenv("TELEGRAM_TOKEN")) \
        .build()
    application.add_handlers(
        [
            CommandHandler("search", search),
            CommandHandler("download", download),
            MessageHandler(COMMAND, get),
        ],
    )

    print("Starting polling!")
    application.run_polling()


if __name__ == "__main__":
    main()
