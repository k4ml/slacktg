
"""
Copyright (c) 2017-present Kamal Bin Mustafa <k4ml@github.io>

Permission to use, copy, modify, and distribute this software for any
purpose with or without fee is hereby granted, provided that the above
copyright notice and this permission notice appear in all copies.

THE SOFTWARE IS PROVIDED "AS IS" AND THE AUTHOR DISCLAIMS ALL WARRANTIES
WITH REGARD TO THIS SOFTWARE INCLUDING ALL IMPLIED WARRANTIES OF
MERCHANTABILITY AND FITNESS. IN NO EVENT SHALL THE AUTHOR BE LIABLE FOR
ANY SPECIAL, DIRECT, INDIRECT, OR CONSEQUENTIAL DAMAGES OR ANY DAMAGES
WHATSOEVER RESULTING FROM LOSS OF USE, DATA OR PROFITS, WHETHER IN AN
ACTION OF CONTRACT, NEGLIGENCE OR OTHER TORTIOUS ACTION, ARISING OUT OF
OR IN CONNECTION WITH THE USE OR PERFORMANCE OF THIS SOFTWARE.
"""

import os
import time
import logging
import threading

import telegram

from slackclient import SlackClient
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters

# Enable logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    level=logging.INFO)

logger = logging.getLogger(__name__)


slack_token = os.environ["SLACK_API_TOKEN"]
sc = SlackClient(slack_token)

tg_token = os.environ['TG_BOT_TOKEN']
bot = telegram.Bot(token=tg_token)
chat_id = int(os.environ['TG_CHAT_ID'])

def get_channel_info(channel_id):
    resp = sc.api_call('channels.info', channel=channel_id)
    if resp['ok']:
        return resp['channel']
    return None

def listen_slack():
    if sc.rtm_connect():
        while True:
            messages = sc.rtm_read()
            for msg in messages:
                if msg['type'] != 'message':
                    continue
                if 'subtype' in msg and msg['subtype'] == 'bot_message':
                    continue
                if msg.get('hidden', False): continue
                print(msg)
                resp = sc.api_call('users.info', user=msg['user'])
                if resp['ok']:
                    user = resp['user']
                    channel = get_channel_info(msg['channel']) or 'N/A'
                    print(user['name'], msg['text'], msg['ts'])
                    ret = bot.sendMessage(chat_id=chat_id, text='#%s:%s:%s> %s' % (channel['name'], msg['ts'], user['name'], msg['text']))
            time.sleep(3)
    else:
        print("Connection Failed")

def error(bot, update, error):
    logger.warn('Update "%s" caused error "%s"' % (update, error))

def listen_telegram():
    offset = -1
    update = None
    channel = '#integrationsandbox'
    while True:
        try:
            updates = bot.get_updates(offset)
        except Exception as e:
            print(e)
            time.sleep(1)
            continue
        for update in updates:
            if update.message.chat.id not in [chat_id]:
                print(update.message.chat.id, chat_id)
                update.message.reply_text('invalid user')
                continue

            thread_ts = None
            reply = update.message.reply_to_message
            if reply:
                reply_parts = reply.text.split(':')
                channel_part = reply_parts[0]
                if channel_part.strip().startswith('#'):
                    channel = channel_part
                thread_ts = reply_parts[1]

            if thread_ts is not None:
                sc.api_call('chat.postMessage', channel=channel, thread_ts=thread_ts,
                            text='From telegram: %s' % update.message.text)
            else:
                sc.api_call('chat.postMessage', channel=channel,
                            text='From telegram: %s' % update.message.text)

            print(update.message.text)
            print(update.message.reply_to_message)
            if 'posted to slack' not in update.message.text:
                update.message.reply_text('posted to slack')

        if update:
            offset = update.update_id + 1
        time.sleep(2)

if __name__ == '__main__':
    tg_thread = threading.Thread(target=listen_telegram)
    slack_thread = threading.Thread(target=listen_slack)
    tg_thread.start()
    slack_thread.start()
