import os
from functools import wraps
import requests
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters
from loguru import logger
from feral_services import jackett, ru_torrent

load_dotenv()

results = {}
last_results = {}
admins = set(os.getenv("ADMINS", "").split(","))


def auth_error_handler(func):
    @wraps(func)
    async def wrapper(update: Update, context):
        try:
            if str(update.effective_user.id) not in admins:
                return
            return await func(update, context)
        except Exception as e:
            logger.exception(f"Error in {func.__name__}: {str(e)}")
            await update.message.reply_text("An error occurred")

    return wrapper


@auth_error_handler
async def search(update: Update, context):
    term = update.message.text.removeprefix("/search").strip()
    error, search_results = jackett.search(term)

    if error or not search_results:
        await update.message.reply_text(error or "No results found")
        return

    user_id = update.effective_user.id
    if msg_id := last_results.get(user_id):
        await context.bot.edit_message_text(
            chat_id=update.effective_chat.id,
            message_id=msg_id,
            text="Previous search results have expired",
            parse_mode="MarkdownV2"
        )

    result_str = jackett.format_and_filter_results(search_results, user_id, results)
    message = await update.message.reply_text(result_str)
    last_results[user_id] = message.message_id


@auth_error_handler
async def download(update: Update, _):
    magnet = update.message.text.removeprefix("/download").strip()
    username = update.effective_user.username or update.effective_user.first_name
    result = ru_torrent.upload_magnet(magnet, "/download", username)
    await update.message.reply_text(result)


@auth_error_handler
async def get(update: Update, _):
    if not (text := update.message.text).startswith("/get"):
        return

    user_id = update.effective_user.id
    user_results = results.get(user_id, {})
    get_id = text.removeprefix("/get").strip()

    if not (result := user_results.get(get_id)):
        await update.message.reply_text("Not a valid item")
        return

    username = update.effective_user.username or update.effective_user.first_name

    if magnet := result.magnet:
        upload_result = ru_torrent.upload_magnet(magnet, result.source, username, result)
        await update.message.reply_text(upload_result)
        return

    if link := result.link:
        site = os.getenv('SITE', '')
        auth_link = link.replace(site, f"{os.getenv('BASIC', '')}@{site}")
        response = requests.get(auth_link, allow_redirects=False)

        if not response.ok:
            await update.message.reply_text(f"Download failed. URL: {auth_link}")
            return

        if response.status_code == 302:
            upload_result = ru_torrent.upload_magnet(
                response.headers["Location"], result.source, username, result
            )
        else:
            upload_result = ru_torrent.upload_torrent(
                response.content, result.source, username, result
            )
        await update.message.reply_text(upload_result)
        return

    await update.message.reply_text("Something went wrong")


def main() -> None:
    app = Application.builder().token(os.getenv("TELEGRAM_TOKEN", "")).build()
    app.add_handlers(
        [
            CommandHandler("search", search),
            CommandHandler("download", download),
            MessageHandler(filters.COMMAND, get),
        ]
    )

    logger.info("Starting bot polling")
    app.run_polling()


if __name__ == "__main__":
    main()