import json
import os

import yaml

CONFIG_PATH = os.path.join(os.path.dirname(__file__), "config.yaml")


class Config:
    @staticmethod
    def get_config():
        if os.path.isfile(CONFIG_PATH):
            return yaml.load(open(CONFIG_PATH, "r"), Loader=yaml.Loader)
        else:
            return json.loads(os.environ["config"])
