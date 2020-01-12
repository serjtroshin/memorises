import json
import requests
from urllib.parse import quote
import pprint

class YandexAPI:
    def __init__(self, src="de", tgt="ru"):
        with open("config.json") as f:
            config = json.load(f)
            keyDict = config["keys"]["YandexDictionary"]
            keyTranslate = config["keys"]["YandexTranslate"]

        self.urlDict = "https://dictionary.yandex.net/api/v1/dicservice.json/lookup?key={}&lang={}-{}&text=".format(keyDict, src, tgt)
        self.urlTranslate = "https://translate.yandex.net/api/v1.5/tr.json/translate?key={}&lang={}-{}&text=".format(keyTranslate, src, tgt)

    def getDictionary(self, word):
        url = self.urlDict + quote(word)
        response = requests.get(
            url
        )
        return response.json()

    def getTranslation(self, word):
        url = self.urlTranslate + quote(word)
        response = requests.get(
            url
        )
        return response.json()

    @staticmethod
    def get_article(gen):
        return {'f' : "die", "m" : "der", 'n' : "das"}[gen]

    def get(self, orig):
        translations = []
        defins = self.getDictionary(orig)['def']  # добавить выбор перевода из нескольких вариантов
        if len(defins) == 0: # если словарь подкачал, обращаемся к пеерводчику
            transl = self.getTranslation(orig)
            if transl["text"][0] == orig:
                return []
            translations.append({
                "orig" : orig,
                "target" : transl["text"][0],
                "examples": None
            })
            return translations
        for defin in defins:
            orig = defin["text"]
            if defin["pos"] == "noun" and "gen" in defin:
                orig = YandexAPI.get_article(defin["gen"]) + " " + orig
            translation = defin["tr"][0]
            examples = [(tr['tr'][0]['text'], tr['text']) for tr in translation['ex']] if 'ex' in translation else None
            target = translation['text']
            translations.append(
                {"orig": orig,
                "target" : target,
                "examples" : examples})
        return translations


if __name__=="__main__":
    yandex_api = YandexAPI()
    pprint.pprint(yandex_api.get("Telefonnumer"))