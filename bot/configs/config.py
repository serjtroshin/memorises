import json
import os

CONFIG_PATH = os.path.join(os.path.dirname(__file__), "config.json")

class Config:
    @staticmethod
    def get_config():
        if os.path.isfile(CONFIG_PATH):
            return json.load(open(CONFIG_PATH, "r"))
        else:
            return json.loads(os.environ["config"])
