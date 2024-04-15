import os
import sys
import json


IS_DEBUG = hasattr(sys, 'gettrace') and sys.gettrace() is not None 


class __config:
    __CONFIG_FILE="./config.json"

    def __init__(self):
        self.settings = {}
        self.load_config()


    def load_config(self):
        # If there's no default config file, create it.
        if not os.path.exists(self.__CONFIG_FILE):
            self.settings = {
                "DEFAULT_BROWSER": "firefox",
                "IMG_DATABASE": "./saucenaoDB.db",
                "TEST_IMG_DATABASE": "./saucenaoDB_TEST.db",
                "HIGH_THRESHOLD": 92.0,
                "LOW_THRESHOLD": 65.0,
                "BLACKLISTED_TERMS": []
            }
            json.dump(self.settings, open(self.__CONFIG_FILE, "w"), ensure_ascii=False, indent=4)
        else:
            self.settings = json.load(open(self.__CONFIG_FILE))
            

config = __config()