
# memorises

**memorises** — a telegram bot for learning a foreign language written in Python 3.7.  
**memorises** stores word cards and periodically notifies the user to recall them following [Ebbinghaus' hypothesis][ebbinghaus].  
Currently, it mainly supports German–Russian language pair 🇩🇪-🇷🇺, but is not limited to it.  
The word/phrase translation  is provided by [Yandex.Dictionary][dictionary] and [Yandex.Translate][translate]. 

## Prerequisites

Install the requirements:
```sh
 pip install -r requirements.txt
 ```

Install [PostgreSQL][postgresql] for managing the database.

## Configuring

You need to obtain API keys for your [Telegram Bot][botfather], [Yandex.Dictionary][dictionary] and [Yandex.Translate][translate].  
Put them and PostgreSQL credentials into the [config file][config_file].

## Running

Start a bot with
```sh
python run.py
```

[ebbinghaus]: https://en.wikipedia.org/wiki/Forgetting_curve
[translate]: http://translate.yandex.ru
[dictionary]: http://api.yandex.ru/dictionary
[postgresql]: https://www.postgresql.org/
[botfather]: https://t.me/botfather
[config_file]: bot/configs/config.yaml
