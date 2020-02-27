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

from .configs.config import Config
from .database import apply_migrations
from .database import create_database
from .utils import Heap
from .api.yandex_api import YandexAPI

from .handlers.start import start
from .handlers.add_flash_card import choose_flash_card, get_reply_meaning, add_flash_cards
from .handlers.delete import delete_flash_card_chosen, delete_flash_card_request
from .handlers.error import error
from .handlers.update import set_timer



TOKEN = Config.get_config()["keys"]["telegramkey"]

REQUEST_KWARGS = None  # if you want to use proxy

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
    add_flash_cards()

    # Get the dispatcher to register handlers
    dp = updater.dispatcher

    # on different commands - answer in Telegram

    dp.add_handler(CommandHandler("start", start))

    dp.add_handler(CommandHandler("delete", delete_flash_card_request))

    dp.add_handler(MessageHandler(Filters.text, choose_flash_card))

    dp.add_handler(
        CallbackQueryHandler(
            get_reply_meaning, pattern=r"^ADD__.*$", pass_chat_data=True
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
