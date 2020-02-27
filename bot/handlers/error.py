
def error(update, context):
    """Log Errors caused by Updates."""
    logger = context.bot_data["logger"]
    logger.warning('Update "%s" caused error "%s"', update, context.error)