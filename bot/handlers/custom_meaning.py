import telegram
from telegram import InlineKeyboardButton
from telegram import InlineKeyboardMarkup

from time import time

from bot.flash_card import FlashCard, get_all_flash_cards
from bot.utils import to_string, parse_string, error_handler


OTHER = "_OTHER_"


@error_handler
def get_meaning(meanings, update, context):
    """
    :param meanings: a set of the different meanings of the word

    Is asking a user to choose between meanings.
    """
    keyboard = [
        [
            InlineKeyboardButton(
                str(meaning["target"]),
                callback_data=to_string(meaning["orig"], i, key="ADD"),
            )
        ]
        for i, meaning in enumerate(meanings)
    ]
    keyboard.append([InlineKeyboardButton("Другое...", callback_data=OTHER)])
    reply_markup = InlineKeyboardMarkup(keyboard, one_time_keyboard=True)
    update.message.reply_text("Возможные варианты:", reply_markup=reply_markup)


@error_handler
def get_reply_meaning(update, context):
    """
    Is called when the user has clicked on the one of the meanings
    """
    cards_buffer_data = context.bot_data["cards_buffer_data"]
    orig, i = parse_string(update.callback_query["data"], nokey=True)
    chat_id = update._effective_chat["id"]
    meanings = cards_buffer_data[to_string(chat_id, orig, key=None)]
    add_flash_card(update, context, meanings[int(i)], chat_id)


@error_handler
def start_setting_custom_meaning(update, context):
    chat_id = update._effective_chat["id"]
    context.bot.send_message(chat_id, "Введите перевод")
    context.user_data["custom"] = True


@error_handler
def get_custom_meaning(update, context):
    """
    Is called when user put custom translation of phrase
    """
    word = context.user_data["word"]
    target = update.message.text.strip()

    meaning = {
        "orig": word,
        "source": word,
        "target": target,
        "examples": [],
        "syns": [],
    }
    return meaning
