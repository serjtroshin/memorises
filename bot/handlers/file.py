from telegram.ext import Updater, MessageHandler, Filters

def downloader(update, context):
    # updater.dispatcher.add_handler(MessageHandler(Filters.document, downloader))
    context.bot.get_file(update.message.document).download()

    # writing to a custom file
    with open("/tmp/bot_input_file.txt", 'wb') as f:
        context.bot.get_file(update.message.document).download(out=f)







