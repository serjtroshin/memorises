from pprint import pprint
from german_nouns.lookup import Nouns

from typing import List
import traceback

from bot.configs.config import Config


class NounDictionary:
    def __init__(self):
        self.nouns = Nouns()

    def _remove_artikel(self, word):
        for beg in ["der", "die", "das"]:
            if word.startswith(beg + " "):
                word = word.lstrip(beg + " ").strip()
        return word

    def _is_in_nouns(self, word: str):
        try:
            self.nouns[word]
            return True
        except Exception:
            return False

    def _get_genus(self, word_info: dict):
        if "genus" in word_info:
            return word_info["genus"]
        else:
            return None

    def _get_full_nominativ(self, word_info: dict):
        try:
            flexion = self._get_flexion(word_info)
            if "lemma" in word_info:
                word = word_info["lemma"]
            else:
                word = ""
            if flexion is not None and 'nominativ singular' in flexion:
                word = flexion['nominativ singular']

            genus = self._get_genus(word_info)
            if genus is None:
                return word
            if genus == "m":
                return f"der {word}"
            if genus == "f":
                return f"die {word}"
            if genus == "n":
                return f"das {word}"
            if genus == "p":
                return f"die {word}"

        except Exception as e:
            print(traceback.print_exc())
            return ""

    def _get_flexion(self, word_info: dict):
        if "flexion" in word_info:
            return word_info["flexion"]
        else:
            return None

    def _get_flexion_unique(self, word_info: dict) -> List[str]:
        try:
            genus = self._get_genus(word_info)
            flexion = self._get_flexion(word_info)
            if flexion is None:
                return []
            if genus is None:
                return sorted(list(set(flexion.values())))
            genus2form = {
                "m": {
                    'nominativ singular': "der",
                    'genitiv singular': 'des',
                    'dativ singular': 'dem',
                    'akkusativ singular': 'den',
                },
                'f': {
                    'nominativ singular': "die",
                    'genitiv singular': 'der',
                    'dativ singular': 'der',
                    'akkusativ singular': 'die',
                },
                'n': {
                    'nominativ singular': "das",
                    'genitiv singular': 'des',
                    'dativ singular': 'dem',
                    'akkusativ singular': 'das',
                },
                'p': {
                    'nominativ singular': "die",
                    'genitiv singular': 'der',
                    'dativ singular': 'den',
                    'akkusativ singular': 'die',
                }
            }
            values = []
            for forma in [
                'nominativ singular',
                'genitiv singular',
                'dativ singular',
                'akkusativ singular'
            ]:
                if forma in flexion:
                    values.append(f"{genus2form[genus][forma]} {flexion[forma]}")

            return values


        except Exception as e:
            print(traceback.print_exc())
            return []

    def get_noun_info(self, word) -> List:
        try:
            word = self._remove_artikel(word)
            if not self._is_in_nouns(word):
                return []
            infos = []
            for word_info in self.nouns[word]:
                info = {}
                info["genus"] = self._get_genus(word_info)
                info["full_noun"] = self._get_full_nominativ(word_info)
                info["flexion_info"] = " | ".join(self._get_flexion_unique(word_info))
                if "genus" in info and info["genus"] is not None:
                    infos.append(info)
        except Exception as e:
            print(traceback.print_exc())
            return []
        return infos


class TranslationDictionary:
    @staticmethod
    def get_dsl_dictionary(path="wikidict-dsl-ru/data/de-ru_wikidict.dsl"):
        german2other = {}
        other2german = {}
        with open(path) as f:
            for i in range(4):
                f.readline()
            while True:
                german = f.readline().strip()
                if german == "":
                    break
                other = f.readline().strip()
                for i in range(3):
                    f.readline()
                german2other[german] = other
                other2german[other] = german
        return german2other, other2german

    def __init__(self, path="wikidict-dsl-ru/data/de-ru_wikidict.dsl"):
        self.german2other, self.other2german = TranslationDictionary.get_dsl_dictionary(path)
        #         print(list(self.other2german.keys())[:100])
        print(f"I know {len(self.german2other)} german words!")

    def _any_match(self, word):
        return word in self.german2other or word in self.other2german

    def _remove_artikel(self, word):
        for beg in ["der", "die", "das"]:
            if word.startswith(beg + " "):
                word = word.lstrip(beg + " ").strip()
        return word

    def get_dict_info(self, word) -> List:
        try:
            word: str = self._remove_artikel(word)
            if not self._any_match(word):
                return []
            infos = []

            if word in self.german2other:
                infos.append({
                    "de": word,
                    "other": self.german2other[word]
                })
            if word.capitalize() in self.german2other:
                infos.append({
                    "de": word.capitalize(),
                    "other": self.german2other[word.capitalize()]
                })
            if word in self.other2german:
                infos.append({
                    "de": self.other2german[word],
                    "other": word
                })
            if word.capitalize() in self.other2german:
                infos.append({
                    "de": self.other2german[word.capitalize()],
                    "other": word.capitalize()
                })
        except Exception as e:
            print(traceback.print_exc())
            return []
        return infos


import pprint
from urllib.parse import quote
import warnings

import requests


class YandexAPI:
    def __init__(self, src="ru", tgt="de"):
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
        self.urlTranslate = "https://translate.api.cloud.yandex.net/translate/v2/translate"
        self.urlDetectLang = "https://translate.api.cloud.yandex.net/translate/v2/detect"

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
        try:
            return response.json()["languageCode"]
        except:
            print(response.json())
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

        defins = []
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


class MetaDictionary:
    def __init__(self):
        self.noun_dictionary = NounDictionary()
        # self.trans_dict = TranslationDictionary()
        # self.samples = Samples()
        self.yandex_api = YandexAPI()

    def get_de_info(self, de_word="Profi", lang="de"):
        translation = self.yandex_api.get(de_word)
        if len(translation) == 0:
            return None, []
        other_word = translation[0]["target"]

        if len(de_word.strip().split()) == 1 and de_word.strip()[0].isupper():
            noun_info = self.noun_dictionary.get_noun_info(de_word)
        else:
            noun_info = []
        # translation_info = self.trans_dict.get_dict_info(word)
        samples = []  # self.samples.get_samples(word)
        return translation[0], noun_info  # , translation_info

    def format_card(self, translation, noun_info):
        if translation is not None:
            print(f"{translation['orig']} | {translation['target']}")
        for noun in noun_info:
            if 'full_noun' in noun:
                print(noun['full_noun'])
            if 'flexion_info' in noun:
                print(noun['flexion_info'])
            break

    def get_info(self, word):
        if self.yandex_api.detectLanguage(word) == "de":
            return self.get_de_info(word)
        else:
            return self.get_other_info(word)

    def get_other_info(self, word="профессионал"):
        translation = self.yandex_api.get(word)
        if len(translation) == 0:
            return None, []
        de_word = translation[0]["target"]
        if len(de_word.strip().split()) == 1 and de_word.strip()[0].isupper():
            noun_info = self.noun_dictionary.get_noun_info(de_word)
        else:
            noun_info = []
        # translation_info = self.trans_dict.get_dict_info(de_word)
        samples = []  # self.samples.get_samples(word)
        return translation[0], noun_info  # , translation_info

    def get(self, word="профессионал"):
        transl, noun_info = [], []
        if self.yandex_api.detectLanguage(word) == "de":
            transl, noun_info = self.get_de_info(word)
        else:
            transl, noun_info = self.get_other_info(word)
        examples = []
        for noun in noun_info:
            if 'full_noun' in noun:
                examples.append(noun['full_noun'])
            if 'flexion_info' in noun:
                examples.append(noun['flexion_info'])
        return [
            {
                "orig": word,
                "source": word,
                "target": transl['target'],
                "examples": examples,
                "syns": None,
            }
        ]

