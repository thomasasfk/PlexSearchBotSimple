from telegram import Update
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, CallbackContext

import requests
import json
import jackett
import ruTorrent

with open('config.json') as json_file:
    config = json.load(json_file)
memory_database = {}
with open(config.get('USERS_FILE')) as json_file:
    users = json.load(json_file)


def save_user(user_id):
    if user_id not in users:
        users.append(user_id)
        with open(config.get('USERS_FILE'), 'w') as outfile:
            json.dump(users, outfile)


def valid_user(user_id):
    return user_id in users


def auth(update: Update, context: CallbackContext) -> None:
    if config.get('PASSWORD') in update.message.text or update.effective_user.id in users:
        save_user(update.effective_user.id)
        update.message.reply_text('Authorized')
    else:
        update.message.reply_text('Wrong password')


def search(update: Update, context: CallbackContext) -> None:
    text = update.message.text
    if valid_user(update.effective_user.id):
        reply = jackett.search(text[7:], update.effective_user.id, memory_database, config)
        update.message.reply_text(reply)
    else:
        update.message.reply_text('Authorise pls')


def get(update: Update, context: CallbackContext) -> None:
    if update.message.text[0:4] != '/get':
        return
    if not valid_user(update.effective_user.id):
        update.message.reply_text('Authorise pls')
        return
    get_id = update.message.text[4:9]

    result = memory_database.get(update.effective_user.id, {}).get(get_id, {})
    resp_msg = 'ewwor'

    if result.get('magnet', False):
        resp_msg = ruTorrent.upload_magnet(result['magnet'], result['label'], config)

    elif result.get('link', False):
        resReq = requests.get(result['link'], allow_redirects=False)
        try:
            if resReq.status_code == 302:
                resp_msg = ruTorrent.upload_magnet(resReq.headers['Location'], result['label'], config)
            elif resReq.ok:
                resp_msg = ruTorrent.upload_torrent(resReq.content, result['label'], config)
        except:
            pass

    update.message.reply_text(resp_msg)


def main() -> None:
    updater = Updater(config.get('TELEGRAM_TOKEN'))
    dispatcher = updater.dispatcher

    dispatcher.add_handler(CommandHandler("search", search))
    dispatcher.add_handler(CommandHandler("auth", auth))
    dispatcher.add_handler(MessageHandler(Filters.command, get))

    updater.start_polling()
    updater.idle()


if __name__ == '__main__':
    main()
