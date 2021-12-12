import telegram
from telegram import InlineKeyboardButton
from telegram import InlineKeyboardMarkup

from datetime import datetime

from bot.flash_card import FlashCard, get_all_flash_cards
from bot.utils import to_string, parse_string, error_handler
from bot.timer import Activity
from bot.configs.settings import TIME_WAIT_FOR_RESPONSE
from bot.api.dict_api import MetaDictionary
from bot.handlers.custom_meaning import get_custom_meaning
from bot.handlers.custom_meaning import get_meaning

yandexAPI = MetaDictionary()


@error_handler
def add_flash_card(update, context, meaning, chat_id):
    """
    :param meaning: one of the meanings, chosen by a user
    :param chat_id: id of the user's chat

    Adds a card to the database and creates the first associated activity.
    """
    activities = context.bot_data["activities"]
    flash_card = FlashCard(
        word=meaning["source"],
        translation=meaning["target"],
        examples=meaning["examples"],
        synonyms=meaning["syns"],
        chat_id=chat_id,
    )
    if flash_card.check_if_exist():
        context.bot.send_message(
            chat_id,
            text=f"Вы уже добавили это слово, вот оно: \n{flash_card}",
            parse_mode=telegram.ParseMode.MARKDOWN,
        )
        return

    flash_card.add_to_database()

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
    context.user_data["last_card"] = flash_card.word


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
def choose_flash_card(update, context):
    """
    Is called, when the user sends the message to the bot.
    It checks if the word is unknown. Otherwise it sends a list of the possible meanings to the user.
    """
    chat_id = update.message.chat_id

    if "custom" in context.user_data:
        meaning = get_custom_meaning(update, context)
        add_flash_card(update, context, meaning, chat_id)
        del context.user_data["custom"]
        return

    cards_buffer = context.bot_data["cards_buffer"]
    cards_buffer_data = context.bot_data["cards_buffer_data"]

    word = update.message.text.strip()
    context.user_data["word"] = word

    if word.find("|") != -1:
        splitted_word = word.split("|")
        if len(splitted_word) != 2:
            context.bot.send_message(
                chat_id,
                text="Некорректный формат произвольной карточки, используйте:\nслово | слово",
            )
            return
        context.user_data["word"], update.message.text = map(
            lambda s: s.strip(), splitted_word
        )
        meaning = get_custom_meaning(update, context)
        add_flash_card(update, context, meaning, chat_id)
        return

    meanings = yandexAPI.get(word)

    get_meaning(meanings, update=update, context=context)
    cards_buffer.push(
        Activity(
            to_string(chat_id, word, key=None),
            datetime.utcnow().timestamp() + TIME_WAIT_FOR_RESPONSE,
        )
    )
    cards_buffer_data[to_string(chat_id, word, key=None)] = meanings


@error_handler
def add_flash_cards(dp):
    """
    On the start of the bot set all the activities.
    """
    activities = dp.bot_data["activities"]
    for record in get_all_flash_cards():
        activities.push(
            Activity(
                record.card_id, record.time_next_delta + record.time_added.timestamp()
            )
        )
