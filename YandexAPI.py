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
        self.urlDetectLang = "https://translate.yandex.net/api/v1.5/tr.json/detect?key={}&hint=de&text=".format(self.keyTranslate)

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

    @staticmethod
    def get_examples(jsn):
        return [(tr['tr'][0]['text'], tr['text']) for tr in jsn['ex']] if 'ex' in jsn else None

    @staticmethod
    def get_synonyms(jsn):
        return [syn['text'] for syn in jsn["syn"]] if "syn" in jsn else None

    @staticmethod
    def add_article(jsn):
        assert 'gen' in jsn
        return YandexAPI.get_article(jsn["gen"]) + " " + jsn["text"]

    def detectLanguage(self, orig):
        url = self.urlDetectLang + quote(orig)
        response = requests.get(
            url
        )
        return response.json()["lang"]

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
        defins = self.getDictionary(orig, src, tgt)['def']
        if len(defins) == 0: # если словарь подкачал, обращаемся к пеерводчику
            transl = self.getTranslation(orig, src, tgt)
            if transl["text"][0] == orig:
                return []
            translations.append({
                "orig" : orig,
                "source": orig,
                "target" : transl["text"][0],
                "examples": None,
                "syns": None
            })
            return translations
        for src_defin in defins:
            source = orig
            if YandexAPI.is_noun(src_defin) and YandexAPI.is_german(src):  # ставим артикль
                source = YandexAPI.add_article(src_defin)
            for translation in src_defin["tr"]:
                target = translation['text']
                if YandexAPI.is_noun(translation) and YandexAPI.is_german(tgt):
                    target = YandexAPI.add_article(translation)
                examples = YandexAPI.get_examples(translation)
                syns = YandexAPI.get_synonyms(translation)
                if syns is not None and YandexAPI.is_german(tgt):
                    syns = list(map(YandexAPI.get_article, syns))
                translations.append(
                    {"orig": orig,
                     "source": source,
                     "target" : target,
                     "examples" : examples,
                     "syns" : syns})
        return translations


if __name__=="__main__":
    yandex_api = YandexAPI()
    pprint.pprint(yandex_api.get("Mädchen"))