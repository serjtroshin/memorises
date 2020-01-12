#!/usr/bin/env python
# -*- coding: utf-8 -*-
# This program is dedicated to the public domain under the CC0 license.

"""
First, a few callback functions are defined. Then, those functions are passed to
the Dispatcher and registered at their respective places.
Then, the bot is started and runs until we press Ctrl-C on the command line.
Usage:
Example of a bot-user conversation using ConversationHandler.
Send /start to initiate the conversation.
Press Ctrl-C on the command line or send a signal to the process to stop the
bot.
"""

import logging
from time import time
from utils import Heap
import json
from time import time
import os

from telegram.ext import (Updater, CommandHandler, MessageHandler, Filters)
from FlashCard import FlashCard
from Timer import Activity
from YandexAPI import YandexAPI
from Config import Config
from database import create_database


TOKEN = Config.get_config()["keys"]["telegramkey"]

REQUEST_KWARGS = None  # if you want to use proxy

# Enable logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    level=logging.INFO)
logger = logging.getLogger(__name__)

yandexAPI = YandexAPI()


flash_cards = {}  # switch to some database
activities = Heap(key=lambda act: act.time)

def add_flash_card(update, context):
    chat_id = update.message.chat_id
    word = update.message.text.strip()
    if word in flash_cards:  # TODO check for every user
        update.message.reply_text("Вы уже добавили это слов, вот оно: \n{}".format(str(flash_cards[word])))
        return

    meanings = yandexAPI.get(word)
    if len(meanings) == 0:
        update.message.reply_text("К сожалению, слово {} мне неизвестно :(".format(word))
        return
    else:
        meanings = meanings[0]  # TODO let user select meaning

    flash_card = FlashCard(word=meanings["orig"],
                           translation=meanings["target"],
                           examples=meanings["examples"],
                           chat_id=chat_id)
    logger.info(f"Adding new card: {flash_card}")
    flash_card.add_to_database()

    saved_flash_card = flash_card.get_from_database()

    print("****************REPEAT TIME", saved_flash_card.time_next_delta + saved_flash_card.time_added.timestamp())

    activities.push(Activity(flash_card, saved_flash_card.time_next_delta + saved_flash_card.time_added.timestamp()))

    update.message.reply_text("Новая карточка!\n" + str(flash_card))


def start(update, context):
    update.message.reply_text('Привет! Я твой помощник в изучении немецкого языка! Напиши какое-нибудь слово на немецком языке, а я дам тебе его значение и напомню, когда ты начнешь его забывать!')
    set_timer(update, context)
    chat_id = update.message.chat_id


def set_timer(update, context):
    """Add a job to the queue."""
    chat_id = update.message.chat_id
    due = 5
    # Add job to queue and stop current one if there is a timer already
    new_job = context.job_queue.run_repeating(check_for_updates, due, context=chat_id)
    context.chat_data['job'] = new_job


def check_for_updates(context):
    job = context.job
    global activities
    cur_time = time()
    acts = []
    while activities.top() is not None and activities.top().time < cur_time:
        act = activities.pop()
        acts.append(act)
    for act in acts:
        time_next = act.flash_card.update()
        act.time += time_next
        activities.push(act)
    for act in acts:
        context.bot.send_message(act.flash_card.chat_id, text="Повторите\n" + str(act.flash_card))


def error(update, context):
    """Log Errors caused by Updates."""
    logger.warning('Update "%s" caused error "%s"', update, context.error)


def main():
    create_database()

    updater = Updater(TOKEN, request_kwargs=REQUEST_KWARGS, use_context=True)

    # Get the dispatcher to register handlers
    dp = updater.dispatcher

    # on different commands - answer in Telegram
    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(MessageHandler(Filters.text, add_flash_card))

    # log all errors
    dp.add_error_handler(error)

    # Start the Bot
    updater.start_polling()

    logger.info("Bot started")

    # Block until you press Ctrl-C or the process receives SIGINT, SIGTERM or
    # SIGABRT. This should be used most of the time, since start_polling() is
    # non-blocking and will stop the bot gracefully.
    updater.idle()


if __name__ == '__main__':
    main()