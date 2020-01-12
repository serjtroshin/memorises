from time import time
from Collins import CollinsAPI
collinsAPI = CollinsAPI()


class FlashCard:
    def __init__(self, word=None, translation=None, definition=None, synonyms=None, examples=None, chat_id=None):
        self.word = word
        self.translation = translation
        self.definition = definition
        self.examples = examples
        self.synonyms = synonyms

        self.chat_id = chat_id
        self.time_added = time()
        self.time_next = 100

    def __str__(self):
        message = "-----Карточка---\n"
        message += "{} | {}".format(self.word, self.translation)
        message += "\n".join(list(
                      map(str, list(filter(lambda x: x is not None, [
                           self.definition]
                    ))))) + "\n"
        if not self.examples is None:
            message += "".join([">> {} | {} \n".format(fr, to) for fr, to in self.examples])
        message += "--------------\n"
        # message = self.word + "\n" + collinsAPI.get_url(self.word) + "\n"
        return message

    def update(self):
        self.time_next *= 10