import os
import sys
import time
import hashlib
import datetime
import imgdatabase
import updateschedule
import saucenao
from saucenao import Result
from colorama import Fore, Style

if sys.platform == "linux":
    sys.path.append(os.path.expanduser("~/pCloudDrive/repos/DanbooruAPI/"))
elif sys.platform == "win32":
    sys.path.append("P:/repos/DanbooruAPI/")

import danbooru

IS_DEBUG = hasattr(sys, 'gettrace') and sys.gettrace() is not None 

danAPI = danbooru.API()
imgDB = imgdatabase.database()


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
    "truckkunart"
]


def search_image(full_path:str):
    return imgDB.execute_query(f"SELECT image_uid FROM Images WHERE full_path=?", [full_path])


def insert_image(full_path):
    file_name, ext = os.path.splitext(os.path.split(full_path)[1])
    img_qry, img_params = ("INSERT INTO Images (full_path, file_name, ext) VALUES (?, ?, ?);", [full_path, file_name, ext])
    return imgDB.execute_change(img_qry, img_params)


def insert_result(image_uid:int, site_flag:int, illust_id:int, similarity:float):
    rst_qry, rst_params = ("INSERT INTO Saucenao_Results (image_uid, site_flag, site_id, similarity, status) VALUES (?, ?, ?, ?, 0);", 
                           [image_uid, site_flag, illust_id, similarity])
    imgDB.execute_change(rst_qry, rst_params)


def skip_file(full_path:str):
    """Skip non-files, files that have already been searched before, not of a valid extension, or has blacklisted terms (mainly for AI art)."""
    return (not os.path.isfile(full_path) or
           not os.path.splitext(full_path)[1] in saucenao.API.get_allowed_extensions() or 
           any(bl in full_path for bl in blacklisted_terms) or
           any(search_image(full_path)))


def format_time(val):
    return (f'{val}' if val > 9 else f'0{val}')


def write_log(msg, name):
    dt = datetime.datetime.now()
    formated_time = f"{dt.date()}_{format_time(dt.hour)}:{format_time(dt.minute)}"
    path = os.path.expanduser("~/Desktop/saucenao_logs/")
    if not os.path.exists(f"{path}"):
        os.makedirs(f"{path}")
    with open(f"{path}{name}_{formated_time}.log", "w") as f:
        f.write(msg)


def __add_favorite(full_path:str, file_name:str, illust_id:int, similarity:int = None):
    danAPI.add_favorite(illust_id)
    print(f"Match found ({similarity or 'via md5'}%): {file_name} favorited to {illust_id}, file removed.")
    if not IS_DEBUG:
        os.remove(full_path)



def __check_danbooru(full_path:str, file_name:str) -> bool:
    """Checks file for MD5 match on Danbooru."""

    params = {}
    with open(full_path, "rb") as file:
        # {"md5": f"{img_md5}"} <- NOTE: DON'T USE. No results gives 404 error. "tags" is safer, returns empty if nothing found.
        params = {"tags": f"md5:{hashlib.md5(file.read()).hexdigest()}"}
    
    json_data = danAPI.get_posts(params)
    if any(json_data):
        for item in json_data:
            __add_favorite(full_path, file_name, item["id"])
        return True
    
    return False


def __process_results(full_path, file_name, response, high_threshold, low_threshold, db_bitmask, image_data):
    """summary: Extract file data and send to saucenao REST API. Log low similarity results to database."""

    # Get a list of all results above the minimum threshold.
    results:list[Result] = list(filter(lambda r: r.header.similarity > low_threshold, [Result(db_bitmask, r) for r in response["results"]]))
    image_uid = insert_image(full_path)
    if not any(results):
        print(f"No valid results found for {file_name}.")
        return

    for result in results:
        if result.header.similarity > high_threshold:
            try:
                # Prevent trading down for a lower res image. Give a slight margin of 5%.
                width, height = image_data["dimensions"]
                post = danAPI.get_post(result.data.dan_id)
                if ((width+height) * .95) > (post["image_width"] + post["image_height"]):
                    print("Danbooru resolution smaller, keeping original image.")
                else:
                    __add_favorite(full_path, file_name, result.data.dan_id, result.header.similarity)
                    # Remove record as well since we won't need it.
                    imgDB.execute_change("DELETE FROM Images WHERE image_uid=?",[image_uid])
                    break # If image is determined a good enough match, move on.
            except Exception as e:
                insert_result(image_uid, saucenao.API.DBMask.index_danbooru, result.data.dan_id, result.header.similarity)
                raise Exception(f"{e}")
        # Anything lower will need to be double checked via 'check-results'.
        else:
            insert_result(image_uid, saucenao.API.DBMask.index_danbooru, result.data.dan_id, result.header.similarity)
            print(f"{file_name} didn't meet similarity quota: {result.header.similarity}%, added record.")


def add_to_danbooru(directory:str, recursive:bool, high_threshold:int, low_threshold:int, schedule:bool):
    db_bitmask = int(saucenao.API.DBMask.index_danbooru)
    sauceAPI = saucenao.API(db_bitmask, low_threshold)

    # Setup list of files to be searched
    all_files: list[str] = []
    if recursive: 
        all_files = [os.path.join(dirpath, f) for dirpath, _, files in os.walk(directory) for f in files]
    else:
        all_files = os.listdir(directory)
    
    try:
        for full_path in all_files:
            if skip_file(full_path):
                continue

            file_name = os.path.split(full_path)[1]
            # Saucenao has a 100 daily search limit, but Dan doesn't. We can save searches by checking image md5 on Dan.
            if not __check_danbooru(full_path, file_name):
                api_response = sauceAPI.send_request(full_path)
                response = api_response["response"]
                image_data = api_response["image"]
                if any(response) and int(response["header"]["results_returned"]) > 0:
                    short_remaining = response["header"]["short_remaining"]
                    long_remaining = response["header"]["long_remaining"]
                    print(f"Remaining Searches 30s|24h: {short_remaining}|{long_remaining}")

                    __process_results(full_path, file_name, response, high_threshold, low_threshold, db_bitmask, image_data)

                    # Check remaining searches.
                    if long_remaining <= 0:
                        print("Reached daily search limit, unable to process more request at this time.")
                        break
                    elif short_remaining <= 0:
                        print("Out of searches for this 30 second period. Sleeping for 25 seconds...")
                        time.sleep(25)
                else:
                    insert_result(full_path, 0, 0, 0)
                    print(f"No results found for {file_name}.")
        # If we've gotten through all files, write a log record to indication as such.
        else:
            msg = f"All files scanned for {directory}"
            name = "saucenao_completed"
            write_log(msg, name)
    except Exception as e:
        error_msg = (str(e))
        name = "saucenao_error"
        write_log(error_msg, name)
        print(f"{Fore.RED}ERROR: {error_msg}{Style.RESET_ALL}")

    # Once finished, set the crontab job to the ending time, this way there will be ample time to refresh the usages.
    if schedule:
        updateschedule.update_crontab_job(directory)