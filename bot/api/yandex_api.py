import pprint
from urllib.parse import quote

import requests

from bot.configs.config import Config


class YandexAPI:
    def __init__(self, src="de", tgt="ru"):
        config = Config.get_config()
        self.keyDict = config["keys"]["YandexDictionary"]
        self.baseHeadersTranslate = {
            "Authorization": config["keys"]["YandexTranslate"]["authorization"]
        }
        self.baseDataTranslate = {
            "folderId": config["keys"]["YandexTranslate"]["folder_id"]
        }
        self.hintsTranslate = [src]

        self.urlDict = (
            "https://dictionary.yandex.net/api/v1/dicservice.json/lookup?"
            "key={}&lang={}-{}&text="
        )
        self.urlTranslate  = "https://translate.api.cloud.yandex.net/translate/v2/translate"
        self.urlDetectLang = "https://translate.api.cloud.yandex.net/translate/v2/detect"

    def getDictionary(self, word, src, tgt):
        url = self.urlDict.format(self.keyDict, src, tgt) + quote(word)
        response = requests.get(url)
        return response.json()

    def getTranslation(self, word, src, tgt) -> str:
        response = requests.post(self.urlTranslate, json={
            **self.baseDataTranslate,
            "sourceLanguageCode": src,
            "targetLanguageCode": tgt,
            "texts": [word]
        }, headers=self.baseHeadersTranslate)
        translations = response.json()["translations"]
        if not translations:
            return word
        return translations[0]["text"]

    @staticmethod
    def get_article(gen):
        try:
            return {"f": "die", "m": "der", "n": "das"}[gen]
        except KeyError:
            return None

    @staticmethod
    def get_examples(jsn):
        return (
            [(tr["tr"][0]["text"], tr["text"]) for tr in jsn["ex"]]
            if "ex" in jsn
            else None
        )

    @staticmethod
    def get_synonyms(jsn):
        return [syn["text"] for syn in jsn["syn"]] if "syn" in jsn else None

    @staticmethod
    def add_article(jsn):
        art = YandexAPI.get_article(jsn["gen"])
        if art is None:
            return jsn["text"]
        return art + " " + jsn["text"]

    def detectLanguage(self, orig):
        response = requests.post(self.urlDetectLang, json={
            **self.baseDataTranslate,
            "text": orig,
            "languageCodeHints": self.hintsTranslate
        }, headers=self.baseHeadersTranslate)
        return response.json()["languageCode"]

    @staticmethod
    def is_noun(jsn):
        return jsn["pos"] == "noun" and "gen" in jsn

    def select_lang(self, orig):
        src = self.detectLanguage(orig)
        reverse = False
        if src == "de":
            tgt = "ru"
        else:
            tgt = "de"
            reverse = True
        return src, tgt, reverse

    @staticmethod
    def is_german(lang):
        return lang == "de"

    def get(self, orig):
        src, tgt, reverse = self.select_lang(orig)
        translations = []
        defins = self.getDictionary(orig, src, tgt)["def"]
        if len(defins) == 0:  # если словарь подкачал, обращаемся к пеерводчику
            transl = self.getTranslation(orig, src, tgt)
            if transl == orig:
                return []
            translations.append(
                {
                    "orig": orig,
                    "source": orig,
                    "target": transl,
                    "examples": None,
                    "syns": None,
                }
            )
            return translations
        for src_defin in defins:
            source = orig
            if YandexAPI.is_noun(src_defin) and YandexAPI.is_german(
                src
            ):  # ставим артикль
                source = YandexAPI.add_article(src_defin)
            for translation in src_defin["tr"]:
                target = translation["text"]
                if YandexAPI.is_noun(translation) and YandexAPI.is_german(tgt):
                    target = YandexAPI.add_article(translation)
                examples = YandexAPI.get_examples(translation)
                syns = YandexAPI.get_synonyms(translation)
                translations.append(
                    {
                        "orig": orig,
                        "source": source,
                        "target": target,
                        "examples": examples,
                        "syns": syns,
                    }
                )
        return translations


if __name__ == "__main__":
    yandex_api = YandexAPI()
    pprint.pprint(yandex_api.get("пока"))
