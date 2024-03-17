import os
import sys
import time
import hashlib
import datetime
from colorama import Fore, Style
import src.updateschedule as updateschedule
import src.saucenao as saucenao
import src.repos.imagerepo as imagerepo
import src.repos.saucenaoresultrepo as saucenaoresultrepo
import src.saucenaoconfig as saucenaoconfig
from src.saucenao import Result
from enum import Enum

if sys.platform == "linux":
    sys.path.append(os.path.expanduser("~/pCloudDrive/repos/DanbooruAPI/"))
elif sys.platform == "win32":
    sys.path.append("P:/repos/DanbooruAPI/")

import danbooru

IS_DEBUG = hasattr(sys, 'gettrace') and sys.gettrace() is not None 

danAPI = danbooru.API()
log_name = None


# For people that generate AI art and such
blacklisted_terms = [
    "AI Art",
    "8co28",
    "AIart_Fring",
    "HoDaRaKe",
    "Shoppy_0909",
    "amoria_ffxiv",
    "eatsleep1111",
    "iolite_aoto",
    "lilydisease",
    "pon_pon_pon_ai",
    "sagawa_gawa",
    "sayaka_aiart",
    "tocotoco365",
    "truckkunart",
    "truckkunsfw"
]


class msg_status(Enum):
    OK = 0
    Warning = 1
    Error = 2



def skip_file(full_path:str):
    """Skip non-files, files that have already been searched before, not of a valid extension, or has blacklisted terms (mainly for AI art)."""
    return (not os.path.isfile(full_path) or
           not os.path.splitext(full_path)[1] in saucenao.API.get_allowed_extensions() or 
           any(bl in full_path for bl in blacklisted_terms) or
           any(imagerepo.search_by_full_path(full_path)))


def format_time(val):
    return (f'{val}' if val > 9 else f'0{val}')


def create_log():
    global log_name

    dt = datetime.datetime.now()
    formated_time = f"{dt.date()}_{format_time(dt.hour)}:{format_time(dt.minute)}"
    path = os.path.expanduser("~/_saucenao_logs/")
    if saucenaoconfig.IS_DEBUG:
        path += "TEST/"
    log_name = f"{path}saucenao_{formated_time}.log"

    if not os.path.exists(f"log_name"):
        if not os.path.exists(f"{path}"):
            os.makedirs(f"{path}")
        with open(f"{log_name}", "+w") as f:
            f.write("")


def append_log(msg):
    with open(f"{log_name}", "+a") as f:
        f.write(f"{msg}\n")


def output(msg:str, status:msg_status = msg_status.OK):
    color = Fore.WHITE
    match status:
        case msg_status.Warning:
            color = Fore.YELLOW
        case msg_status.Error:
            color = Fore.RED
            
    print(f"{color}{(msg if status != msg_status.Error else f'ERROR {msg}')}{Style.RESET_ALL}") 
    append_log(msg)


def add_favorite(full_path:str, file_name:str, illust_id:int, similarity:int = None):
    danAPI.add_favorite(illust_id)
    output(f"Match found ({similarity or 'via md5'}%): {file_name} favorited to {illust_id}, file removed.")
    if not IS_DEBUG:
        os.remove(full_path)


def check_danbooru(full_path:str, file_name:str, md5:str) -> bool:
    """Checks file for MD5 match on Danbooru."""

    # {"md5": f"{img_md5}"} <- NOTE: DON'T USE. No results gives 404 error. "tags" is safer, returns empty if nothing found.
    params = {"tags": f"md5:{md5}"}
    
    json_data = danAPI.get_posts(params)
    if any(json_data):
        for item in json_data:
            add_favorite(full_path, file_name, item["id"])
        return True
    
    return False


def process_results(full_path, file_name, md5, response, high_threshold, low_threshold, db_bitmask, image_data):
    """summary: Extract file data and send to saucenao REST API. Log low similarity results to database."""

    # Get a list of all results above the minimum threshold.
    results:list[Result] = list(filter(lambda r: r.header.similarity > low_threshold, [Result(db_bitmask, r) for r in response["results"]]))
    image_uid = imagerepo.insert_image(full_path, md5)
    if not any(results):
        output(f"No valid results found for {file_name}.")
        return

    for result in results:
        if result.header.similarity > high_threshold:
            try:
                # Prevent trading down for a lower res image. Give a slight margin of 5%.
                width, height = image_data["dimensions"]
                post = danAPI.get_post(result.data.dan_id)
                if ((width+height) * .95) > (post["image_width"] + post["image_height"]):
                    output(f"Danbooru resolution smaller, keeping {file_name}.", msg_status.Warning)
                else:
                    add_favorite(full_path, file_name, result.data.dan_id, result.header.similarity)
                    # Remove record as well since we won't need it.
                    imagerepo.delete_image(image_uid)
                    break # If image is determined a good enough match, move on.
            except Exception as e:
                saucenaoresultrepo.insert_result(image_uid, saucenao.API.DBMask.index_danbooru, result.data.dan_id, result.header.similarity)
                raise Exception(f"{e}")
        # Anything lower will need to be double checked via 'check-results'.
        else:
            saucenaoresultrepo.insert_result(image_uid, saucenao.API.DBMask.index_danbooru, result.data.dan_id, result.header.similarity)
            output(f"{file_name} didn't meet similarity quota: {result.header.similarity}%, added record.")


def add_to_danbooru(directory:str, recursive:bool, high_threshold:int, low_threshold:int, schedule:bool):
    db_bitmask = int(saucenao.API.DBMask.index_danbooru)
    sauceAPI = saucenao.API(db_bitmask, low_threshold)

    all_files: list[str] = []
    if recursive: 
        all_files = [os.path.join(dirpath, f) for dirpath, _, files in os.walk(directory) for f in files]
    else:
        all_files = os.listdir(directory)
    
    try:
        create_log()
        for full_path in all_files:
            if skip_file(full_path):
                continue

            file_name = os.path.split(full_path)[1]
            with open(full_path, "rb") as file:
                md5 = hashlib.md5(file.read()).hexdigest()

            # Check DB to ensure image isn't a duplicate.
            md5_response = imagerepo.check_existing_file(md5, full_path)
            match md5_response["status"]:
                case 1: # Duplicate
                    output(md5_response["msg"], msg_status.Warning)    
                    os.remove(full_path)
                    continue
                case 2: # Renamed/Moved
                    output(md5_response["msg"], msg_status.Warning)    
                    continue
                
            # Saucenao has a 100 daily search limit, but Dan doesn't. We can save searches by checking the image's md5 on Dan.
            if not check_danbooru(full_path, file_name, md5):
                api_response = sauceAPI.send_request(full_path)
                response = api_response["response"]
                image_data = api_response["image"]
                if any(response) and int(response["header"]["results_returned"]) > 0:
                    short_remaining = response["header"]["short_remaining"]
                    long_remaining = response["header"]["long_remaining"]
                    print(f"Remaining Searches 30s|24h: {short_remaining}|{long_remaining}")

                    process_results(full_path, file_name, md5, response, high_threshold, low_threshold, db_bitmask, image_data)

                    # Check remaining searches.
                    if long_remaining <= 0:
                        output("Reached daily search limit, unable to process more request at this time.")
                        break
                    elif short_remaining <= 0:
                        print("Out of searches for this 30 second period. Sleeping for 25 seconds...")
                        time.sleep(25)
                else:
                    imagerepo.insert_image(full_path, md5)
                    output(f"No results found for {file_name}.")
        # If we've gotten through all the files, write a log record to indication as such.
        else:
            output(f"All files scanned for {directory}")
    except Exception as e:
        output(str(e), msg_status.Error) 

    # Once finished, set the crontab job to the ending time, this way there will be ample time to refresh all usages.
    if schedule:
        updateschedule.update_crontab_job(directory)