
def error(update, context):
    """Log Errors caused by Updates."""
    global logger
    logger.warning('Update "%s" caused error "%s"', update, context.error)