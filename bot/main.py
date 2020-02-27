#!/usr/bin/env python
# -*- coding: utf-8 -*-
import logging
from time import time

import telegram
from telegram.ext import CallbackQueryHandler
from telegram.ext import CommandHandler
from telegram.ext import Filters
from telegram.ext import MessageHandler
from telegram.ext import Updater

from bot.configs.config import Config
from bot.database import apply_migrations
from bot.database import create_database
from bot.utils import Heap
from bot.api.yandex_api import YandexAPI

from bot.handlers.start import start
from bot.handlers.add_flash_card import choose_flash_card, get_reply_meaning, add_flash_cards
from bot.handlers.delete import delete_flash_card_chosen, delete_flash_card_request
from bot.handlers.error import error
from bot.handlers.update import set_timer
from bot.handlers.custom_meaning import start_setting_custom_meaning, OTHER

config = Config.get_config()

TOKEN = config["keys"]["telegramkey"]

REQUEST_KWARGS = config["proxy"] if "proxy" in config else None

# Enable logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

yandexAPI = YandexAPI()

# Every time a card added to the bot, the card is stored in the database
# and the fist activity for the card is created.
# The activity is a pair of card_id and time it should be shown.
# Every n seconds check_for_updated function is looking for ready activities.
# If the activity is ready (the top of the heap has the `time` value less than current time())
# it is extracted from the heap and added one more time with increased time delay.
# Note: if the bot goes down, all the activities are to be recreated from the card info, when the bot is up
activities = Heap(key=lambda act: act.time)

# a buffer that stores cards until the user choose one
# on that event the chosen card is exracted from the buffer
cards_buffer = Heap(key=lambda act: act.time)  # time -> chat_id
cards_buffer_data = {}  # chat_id -> data



def prepare():
    create_database()
    apply_migrations()

    updater = Updater(TOKEN, request_kwargs=REQUEST_KWARGS, use_context=True)

    j = updater.job_queue
    set_timer(j)


    # Get the dispatcher to register handlers
    dp = updater.dispatcher

    # set data
    dp.bot_data["activities"] = activities
    dp.bot_data["cards_buffer"] = cards_buffer
    dp.bot_data["cards_buffer_data"] = cards_buffer_data
    dp.bot_data["logger"] = logger
    add_flash_cards(dp)

    # on different commands - answer in Telegram

    dp.add_handler(CommandHandler("start", start))

    dp.add_handler(CommandHandler("delete", delete_flash_card_request))

    
    dp.add_handler(MessageHandler(Filters.text, choose_flash_card, pass_user_data=True))

    dp.add_handler(
        CallbackQueryHandler(
            get_reply_meaning, pattern=r"^ADD__.*$", pass_chat_data=True
        )
    )

    dp.add_handler(
        CallbackQueryHandler(
            start_setting_custom_meaning, pattern=OTHER, pass_chat_data=True
        )
    )
    
    dp.add_handler(
        CallbackQueryHandler(
            delete_flash_card_chosen, pattern=r"^DELETE__.*$", pass_chat_data=True
        )
    )

    # log all errors
    dp.add_error_handler(error)

    return updater

def main():
    updater = prepare()
    # Start the Bot
    updater.start_polling()

    logger.info("Bot started")

    # Block until you press Ctrl-C or the process receives SIGINT, SIGTERM or
    # SIGABRT. This should be used most of the time, since start_polling() is
    # non-blocking and will stop the bot gracefully.
    updater.idle()


if __name__ == "__main__":
    main()
