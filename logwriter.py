import os
import sys
import saucenaoconfig
from colorama import Fore, Style

config = saucenaoconfig.config()


def check_log_exists():
    return os.path.exists(config["LOG_NAME"])


def append_log(line:str):
    write_log([line], "+a")


def write_log(lines:list[str], permission:str):
    with open(config["LOG_NAME"], permission) as f:
        f.writelines(lines)


def extract_log() -> list[str]:
    """Pull records from log file."""
    if check_log_exists():
        with open(config["LOG_NAME"]) as f:
            return f.readlines()


    
    