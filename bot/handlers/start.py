


def start(update, context):
    update.message.reply_text(
        "Привет! Я твой помощник в изучении немецкого языка! "
        "Напиши какое-нибудь слово, а я дам тебе его значение и напомню, "
        "когда ты начнешь его забывать! "
        "Переведено сервисом «Яндекс.Переводчик», "
        "реализовано с помощью сервиса «API «Яндекс.Словарь»"
        "(http://translate.yandex.ru,  http://api.yandex.ru/dictionary)"
    )