

class CollinsAPI:
    def __init__(self):
        self.german_english_url = "https://www.collinsdictionary.com/dictionary/german-english"

    def get_url(self, word):
        return self.german_english_url + "/" + word
