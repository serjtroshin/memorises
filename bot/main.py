#!/usr/bin/env python
# -*- coding: utf-8 -*-
import logging
from time import time

import telegram
from telegram import InlineKeyboardButton
from telegram import InlineKeyboardMarkup
from telegram.ext import CallbackQueryHandler
from telegram.ext import CommandHandler
from telegram.ext import Filters
from telegram.ext import MessageHandler
from telegram.ext import Updater

from .configs.config import Config
from .database import apply_migrations
from .database import create_database
from .flash_card import FlashCard
from .flash_card import get_all_flash_cards
from .configs.settings import TIME_WAIT_FOR_RESPONSE
from .timer import Activity
from .utils import to_string, parse_string
from .utils import Heap
from .api.yandex_api import YandexAPI


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

CHOOSING, REPLY, EXIT = range(3)


def get_meaning(meanings, update, context):
    """
    :param meanings: a set of the different meanings of the word

    Is asking a user to choose between meanings.
    """
    keyboard = [
        [
            InlineKeyboardButton(
                str(meaning["target"]), callback_data=to_string(meaning["orig"], i, key="ADD")
            )
        ]
        for i, meaning in enumerate(meanings)
    ]
    reply_markup = InlineKeyboardMarkup(keyboard, one_time_keyboard=True)
    update.message.reply_text("Возможные варианты:", reply_markup=reply_markup)


def get_reply_meaning(update, context):
    """
    Is called when the user has clicked on the one of the mearnings
    """
    orig, i = parse_string(update.callback_query["data"], nokey=True)
    chat_id = update._effective_chat["id"]
    meanings = cards_buffer_data[to_string(chat_id, orig, key=None)]
    add_flash_card(update, context, meanings[int(i)], chat_id)

    return CHOOSING


def choose_flash_card(update, context):
    """
    Is called, when the user sends the message to the bot.
    It checks if the word is unknown. Otherwise it sends a list of the possible meanings to the user.
    """
    chat_id = update.message.chat_id
    word = update.message.text.strip()

    meanings = yandexAPI.get(word)
    if len(meanings) == 0:
        update.message.reply_text(
            "К сожалению, слово {} мне неизвестно :(".format(word)
        )
        return  # предложить пользователю ввести свой вариант или удалить карточку
    else:
        get_meaning(meanings, update=update, context=context)
        cards_buffer.push(
            Activity(to_string(chat_id, word, key=None), time() + TIME_WAIT_FOR_RESPONSE)
        )
        cards_buffer_data[to_string(chat_id, word, key=None)] = meanings

    return REPLY


def add_flash_card(update, context, meaning, chat_id):
    """
    :param meaning: one of the meanings, chosen by a user
    :param chat_id: id of the user's chat

    Adds a card to the database and creates the first associated activity.
    """
    flash_card = FlashCard(
        word=meaning["source"],
        translation=meaning["target"],
        examples=meaning["examples"],
        synonyms=meaning["syns"],
        chat_id=chat_id,
    )
    if flash_card.chech_if_exist():
        context.bot.send_message(
            chat_id,
            text=f"Вы уже добавили это слово, вот оно: \n{flash_card}",
            parse_mode=telegram.ParseMode.MARKDOWN,
        )
        return
    logger.info(f"Adding new card: {flash_card}")

    flash_card.add_to_database()

    print(flash_card.time_next_delta)
    activities.push(
        Activity(
            flash_card.card_id,
            flash_card.time_next_delta + flash_card.time_added.timestamp(),
        )
    )

    context.bot.send_message(
        chat_id,
        text="Новая карточка!\n" + str(flash_card),
        parse_mode=telegram.ParseMode.MARKDOWN,
    )


def delete_flash_card_request(update, context):
    """
    Is called when a `/delete [phrase]` method is called.
    Returns the possible cards associated with phrase to be deleted.
    User may choose one of the cards to delete or ignore.
    """
    chat_id = update.message.chat_id
    word = context.args[0].strip()  # todo добавить проверку
    records = FlashCard.findall_in_database(word, str(chat_id))
    keyboard = [
        [
            InlineKeyboardButton(
                f"{record.phrase} | {record.translation}",
                callback_data=f"DELETE__{record.card_id}",
            )
        ]
        for i, record in enumerate(records)
    ]
    reply_markup = InlineKeyboardMarkup(keyboard, one_time_keyboard=True)
    update.message.reply_text("Какую карточку удалить?:", reply_markup=reply_markup)


def delete_flash_card_chosen(update, context):
    """
    Called when the user clicked on the flash card from the list created by `delete_flash_card_request`.
    Permanently removes a card from the database.
    """
    card_id = int(parse_string(update.callback_query["data"], nokey=True))
    chat_id = update._effective_chat["id"]
    FlashCard.delete(card_id)
    context.bot.send_message(
        chat_id, text="Карточка успешно удалена", parse_mode=telegram.ParseMode.MARKDOWN
    )


def start(update, context):
    print(context)
    logger.info(f"Start")
    update.message.reply_text(
        "Привет! Я твой помощник в изучении немецкого языка! "
        "Напиши какое-нибудь слово, а я дам тебе его значение и напомню, "
        "когда ты начнешь его забывать! "
        "Переведено сервисом «Яндекс.Переводчик», "
        "реализовано с помощью сервиса «API «Яндекс.Словарь»"
        "(http://translate.yandex.ru,  http://api.yandex.ru/dictionary)"
    )
    return CHOOSING


def set_timer(j):
    """Add a job to the queue."""
    due = 5
    j.run_repeating(check_for_updates, due)


def check_for_updates(context):
    """
    Checks activities in a loop. If activity is ready handles it, resetting it's time.
    """
    global activities
    cur_time = time()
    acts = []
    while activities.top() is not None and activities.top().time < cur_time:
        act = activities.pop()
        acts.append(act)
    for act in acts:
        flash_card = FlashCard(card_id=act.data)
        try:
            flash_card.fill_from_database()
            time_next = flash_card.update()
            act.time += time_next
            activities.push(act)
            context.bot.send_message(
                flash_card.chat_id,
                text="Повторите\n" + str(flash_card),
                parse_mode=telegram.ParseMode.MARKDOWN,
            )
        except Exception as e:
            logger.info(e)

    while cards_buffer.top() is not None and cards_buffer.top().time < cur_time:
        k = cards_buffer.pop().data
        del cards_buffer_data[k]


def add_flash_cards():
    """
    On the start of the bot set all the activities.
    """
    for record in get_all_flash_cards():
        activities.push(
            Activity(
                record.card_id, record.time_next_delta + record.time_added.timestamp()
            )
        )


def error(update, context):
    """Log Errors caused by Updates."""
    logger.warning('Update "%s" caused error "%s"', update, context.error)


def main():
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
            get_reply_meaning, pattern=r"^ADD__.*__\d*$", pass_chat_data=True
        )
    )
    dp.add_handler(
        CallbackQueryHandler(
            delete_flash_card_chosen, pattern=r"^DELETE__[\w\d]*$", pass_chat_data=True
        )
    )

    # log all errors
    dp.add_error_handler(error)

    # Start the Bot
    updater.start_polling()

    logger.info("Bot started")

    # Block until you press Ctrl-C or the process receives SIGINT, SIGTERM or
    # SIGABRT. This should be used most of the time, since start_polling() is
    # non-blocking and will stop the bot gracefully.
    updater.idle()


if __name__ == "__main__":
    main()
