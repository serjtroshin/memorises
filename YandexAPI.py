import json
import requests
from urllib.parse import quote
import pprint
from Config import Config

class YandexAPI:
    def __init__(self, src="de", tgt="ru"):
        config = Config.get_config()
        self.keyDict = config["keys"]["YandexDictionary"]
        self.keyTranslate = config["keys"]["YandexTranslate"]

        self.urlDict = "https://dictionary.yandex.net/api/v1/dicservice.json/lookup?key={}&lang={}-{}&text="
        self.urlTranslate = "https://translate.yandex.net/api/v1.5/tr.json/translate?key={}&lang={}-{}&text="
        self.urlDetectLang = "https://translate.yandex.net/api/v1.5/tr.json/detect?key={}&text=".format(self.keyTranslate)

    def getDictionary(self, word, src, tgt):
        url = self.urlDict.format(self.keyDict, src, tgt) + quote(word)
        response = requests.get(
            url
        )
        return response.json()

    def getTranslation(self, word, src, tgt):
        url = self.urlTranslate.format(self.keyTranslate, src, tgt) + quote(word)
        response = requests.get(
            url
        )
        return response.json()

    @staticmethod
    def get_article(gen):
        return {'f' : "die", "m" : "der", 'n' : "das"}[gen]

    def detectLanguage(self, orig):
        url = self.urlDetectLang + quote(orig)
        response = requests.get(
            url
        )
        return response.json()["lang"]


    def get(self, orig):
        src = self.detectLanguage(orig)
        reverse=False
        if src == "de":
            tgt = "ru"
        else:
            tgt = "de"
            reverse=True
        translations = []
        defins = self.getDictionary(orig, src, tgt)['def']  # добавить выбор перевода из нескольких вариантов
        if len(defins) == 0: # если словарь подкачал, обращаемся к пеерводчику
            transl = self.getTranslation(orig, src, tgt)
            if transl["text"][0] == orig:
                return []
            translations.append({
                "orig" : orig if not reverse else transl["text"][0],
                "target" : transl["text"][0] if not reverse else orig,
                "examples": None
            })
            return translations
        for defin in defins:
            orig = defin["text"]
            translation = defin["tr"][0]
            target = translation['text']
            if defin["pos"] == "noun" and "gen" in defin and src == "de": # ставим артикль
                orig = YandexAPI.get_article(defin["gen"]) + " " + orig
            elif translation["pos"] == "noun" and "gen" in translation and tgt == "de":
                target = YandexAPI.get_article(translation["gen"]) + " " + target
            examples = [(tr['tr'][0]['text'], tr['text']) for tr in translation['ex']] if 'ex' in translation else None

            translations.append(
                {"orig": orig if not reverse else target,
                "target" : target if not reverse else orig,
                "examples" : examples})
        return translations


if __name__=="__main__":
    yandex_api = YandexAPI()
    pprint.pprint(yandex_api.get("кот"))