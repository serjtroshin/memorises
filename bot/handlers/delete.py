import telegram
from telegram import InlineKeyboardButton
from telegram import InlineKeyboardMarkup

from time import time

from bot.flash_card import FlashCard
from bot.utils import to_string, parse_string, error_handler


@error_handler
def delete_flash_card_request(update, context):
    """
    Is called when a `/delete [phrase]` method is called.
    Returns the possible cards associated with phrase to be deleted.
    User may choose one of the cards to delete or ignore.
    """
    chat_id = update.message.chat_id
    word = " ".join(context.args).strip()
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


@error_handler
def delete_flash_card_chosen(update, context):
    """
    Called when the user clicked on the flash card from the list created by `delete_flash_card_request`.
    Permanently removes a card from the database.
    """
    card_id = int(parse_string(update.callback_query["data"], nokey=True)[0])
    chat_id = update._effective_chat["id"]
    FlashCard.delete(card_id)
    context.bot.send_message(
        chat_id, text="Карточка успешно удалена", parse_mode=telegram.ParseMode.MARKDOWN
    )
