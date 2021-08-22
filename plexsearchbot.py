import time

from telegram import Update
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, CallbackContext

import requests
import json
import jackett
import ruTorrent
import schedule
import datetime

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


stuff_to_poll = {}


def poll_all():
    print(f'Polling now: {datetime.datetime.now()}')

    for term, stuff in stuff_to_poll.items():
        poll_term(term, stuff[1])


def poll_term(term, update: Update):
    new_results = jackett.search(term, config)
    old_results = stuff_to_poll.get(term)[0]
    if len(new_results) != len(old_results) and len(new_results) > 0:
        update.message.reply_text(f'Result count changed for term: {term}\nOld Results: {len(old_results)}, New '
                                  f'Results: {len(new_results)}')
    stuff_to_poll[term] = (new_results, update)


def search(update: Update, context: CallbackContext) -> None:
    text = update.message.text
    if valid_user(update.effective_user.id):
        term = text[7:]
        poll = False
        if '--poll' in text or '—poll' in text:
            poll = True
            term = term.replace('--poll', '')
            term = term.replace('—poll', '')
            term = term.strip()
        results = jackett.search(term, config)
        reply = jackett.get_str_results(results, update.effective_user.id,
                                        memory_database) if results else "No results found"
        update.message.reply_text(reply)
        if poll:
            stuff_to_poll[term] = (results, update)
            update.message.reply_text(f'Also added term [{term}] to daily polling')
    else:
        update.message.reply_text('Authorise pls')


def remove(update: Update, context: CallbackContext) -> None:
    text = update.message.text
    term = text[7:].strip()
    if valid_user(update.effective_user.id):
        if term in stuff_to_poll:
            del stuff_to_poll[term]
            update.message.reply_text(f'Removed term [{term}] from daily polling')
        else:
            update.message.reply_text(f'Term [{term}] not actively polled')


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


def polly():
    print("I'm working...")


def main() -> None:
    updater = Updater(config.get('TELEGRAM_TOKEN'))
    dispatcher = updater.dispatcher

    dispatcher.add_handler(CommandHandler("search", search))
    dispatcher.add_handler(CommandHandler("remove", remove))
    dispatcher.add_handler(CommandHandler("auth", auth))
    dispatcher.add_handler(MessageHandler(Filters.command, get))

    updater.start_polling()
    schedule.every().day.at("10:00").do(poll_all)

    while True:
        schedule.run_pending()
        time.sleep(1)


if __name__ == '__main__':
    main()
