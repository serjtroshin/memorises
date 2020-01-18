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
from utils import Heap, get_hash, parse_hash
import json
from time import time
import os

import telegram
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup
from telegram.ext import (Updater, CommandHandler, ConversationHandler, MessageHandler, Filters, CallbackQueryHandler)
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

activities = Heap(key=lambda act: act.time)

cards_buffer = Heap(key=lambda act: act.time) # time -> chat_id
cards_buffer_data = {} # chat_id -> data
TIME_WAIT_FOR_RESPONSE=10000 # sec

CHOOSING, REPLY, EXIT = range(3)



def get_meaning(meanings, update, context):
    print("get_meaning")
    keyboard = [[InlineKeyboardButton(str(meaning["target"]), callback_data=get_hash(meaning["orig"], i, "__"))] for i,meaning in enumerate(meanings)]
    reply_markup = InlineKeyboardMarkup(keyboard, one_time_keyboard=True)
    update.message.reply_text('Please choose:', reply_markup=reply_markup)

def get_reply_meaning(update, context):
    print("get_reply_meaning")
    orig, i = parse_hash(update.callback_query["data"], "__")
    chat_id = update._effective_chat["id"]
    meanings = cards_buffer_data[get_hash(chat_id, orig)]
    add_flash_card(update, context, meanings[int(i)], chat_id)

    return CHOOSING

def choose_flash_card(update, context):
    print("choose_flash_card")
    chat_id = update.message.chat_id
    word = update.message.text.strip()

    meanings = yandexAPI.get(word)
    if len(meanings) == 0:
        update.message.reply_text("К сожалению, слово {} мне неизвестно :(".format(word))
        return # предложить пользователю ввести свой вариант или удалить карточку
    else:
        get_meaning(meanings, update=update, context=context)  # TODO let user select meaning
        cards_buffer.push(Activity(get_hash(chat_id, word), time() + TIME_WAIT_FOR_RESPONSE))
        cards_buffer_data[get_hash(chat_id, word)] = meanings

    return REPLY

def add_flash_card(update, context, meaning, chat_id):
    print("add_flash_card")
    flash_card = FlashCard(word=meaning["orig"],
                           translation=meaning["target"],
                           examples=meaning["examples"],
                           synonyms=meaning["syns"],
                           chat_id=chat_id)
    if flash_card.chech_if_exist():
        context.bot.send_message(chat_id, text="Вы уже добавили это слово, вот оно: \n{}".format(str(flash_card)),
                                 parse_mode=telegram.ParseMode.MARKDOWN)
        return
    logger.info(f"Adding new card: {flash_card}")
    flash_card.add_to_database()

    saved_flash_card = flash_card.get_from_database()

    # print("****************REPEAT TIME", saved_flash_card.time_next_delta + saved_flash_card.time_added.timestamp())

    activities.push(Activity(flash_card, saved_flash_card.time_next_delta + saved_flash_card.time_added.timestamp()))

    context.bot.send_message(chat_id, text="Новая карточка!\n" + str(flash_card),
                             parse_mode=telegram.ParseMode.MARKDOWN)

def start(update, context):
    logger.info(f"Start")
    update.message.reply_text('Привет! Я твой помощник в изучении немецкого языка! Напиши какое-нибудь слово, а я дам тебе его значение и напомню, когда ты начнешь его забывать!')
    set_timer(update, context)
    chat_id = update.message.chat_id
    return CHOOSING

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
        context.bot.send_message(act.flash_card.chat_id, text="Повторите\n" + str(act.flash_card),
                                 parse_mode=telegram.ParseMode.MARKDOWN)

    while cards_buffer.top() is not None and cards_buffer.top().time < cur_time:
        k = cards_buffer.pop().flash_card
        del cards_buffer_data[k]

def error(update, context):
    """Log Errors caused by Updates."""
    logger.warning('Update "%s" caused error "%s"', update, context.error)

def main():
    create_database()

    updater = Updater(TOKEN, request_kwargs=REQUEST_KWARGS, use_context=True)

    # Get the dispatcher to register handlers
    dp = updater.dispatcher

    # on different commands - answer in Telegram


    dp.add_handler(CommandHandler('start', start))

    dp.add_handler(MessageHandler(Filters.text,
                                      choose_flash_card))

    dp.add_handler(CallbackQueryHandler(get_reply_meaning, pattern="^.*__\d*$", pass_chat_data=True))

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