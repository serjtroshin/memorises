import json
import os

import yaml

CONFIG_PATH = os.path.join(os.path.dirname(__file__), "config.yaml")
url = os.environ.get("DATABASE_URL")


class Config:
    @staticmethod
    def get_config():
        if url is None:
            return yaml.load(open(CONFIG_PATH, "r"), Loader=yaml.Loader)
        else:
            return json.loads(os.environ["config"])
