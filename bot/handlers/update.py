import telegram

from time import time

from bot.utils import to_string, parse_string, error_handler
from bot.flash_card import FlashCard


def set_timer(j):
    """Add a job to the queue."""
    due = 5
    j.run_repeating(check_for_updates, due)


@error_handler
def check_for_updates(context):
    """
    Checks activities in a loop. If activity is ready handles it, resetting it's time.
    """
    logger = context.bot_data["logger"]
    cards_buffer = context.bot_data["cards_buffer"]
    cards_buffer_data = context.bot_data["cards_buffer_data"]
    activities = context.bot_data["activities"]

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
            logger.exception(e)

    while cards_buffer.top() is not None and cards_buffer.top().time < cur_time:
        k = cards_buffer.pop().data
        del cards_buffer_data[k]
