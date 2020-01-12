import os
import json

class Config:
    @staticmethod
    def get_config():
        config_name = "config.json"
        if os.path.isfile(config_name):
            return json.load(open(config_name, "r"))
        else:
            return json.loads(os.environ["config"])