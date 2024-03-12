import os
import json

class config:
    __CONFIG_FILE="./config.json"

    def __init__(self):
        self.settings = {}
        self.load_config()


    def load_config(self):
        # If there's no default config file, create it.
        if not os.path.exists(self.__CONFIG_FILE):
            self.settings = {
                "DEFAULT_BROWSER": "firefox",
                "LOG_NAME": "./saucenao_log.txt",
                "DATABASE_NAME": "./saucenaoDB.db"
            }
            json.dump(self.settings, open(self.__CONFIG_FILE, "w"))
        else:
            self.settings = json.load(open(self.__CONFIG_FILE))
            
