import os
import sys
import time
import hashlib
import datetime
import logwriter
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
    results = imgDB.execute_query(f"SELECT image_uid FROM Images WHERE full_path=?", [full_path])
    return results


def image_query(full_path) -> int:
    file_name, ext = os.path.splitext(os.path.split(full_path)[1])
    return ("INSERT INTO Images (full_path, file_name, ext) VALUES (?, ?, ?);", [full_path, file_name, ext])


def results_query(image_id, site_flag, illust_id, similarity):
    return ("INSERT INTO Saucenao_Results (image_uid, site_flag, site_id, similarity, status) VALUES (?, ?, ?, ?, 0);", 
            [image_id, site_flag, illust_id, similarity])


def insert_result(full_path:str, site_flag:int, illust_id:int, similarity:float, found:bool, image_uid = None):
    if image_uid == None:
        img_qry, img_params = image_query(full_path)
        image_uid = imgDB.execute_change(img_qry, img_params)

    if found:
        rst_qry, rst_params = results_query(image_uid, site_flag, illust_id, similarity)
        imgDB.execute_change(rst_qry, rst_params)
    
    return image_uid

def skip_file(fname:str):
    """Skip non-files, files that have already been searched before, not of a valid extension, or has blacklisted terms (mainly for AI art)."""
    if not os.path.isfile(fname):
        return True
    elif any(search_image(fname)):
        return True
    elif not os.path.splitext(fname)[1] in saucenao.API.get_allowed_extensions():
        return True
    elif any(bl in fname for bl in blacklisted_terms):
        return True
    
    return False


def write_to_log(msg, name):
    dt = datetime.datetime.now()
    strdt = str(dt.date()) + "_" + str(dt.hour) + str(dt.minute)
    path = os.path.expanduser("~/Desktop/saucenao_logs/")
    if not os.path.exists(f"{path}"):
        os.makedirs(f"{path}")
    logwriter.write_log(path + f"{name}_{strdt}.log", msg, "w")


def __add_favorite(full_path:str, file_name:str, illust_id:int, similarity:int = None):
    danAPI.add_favorite(illust_id)
    print(f"Match found ({similarity or 'via md5'}%): {file_name} favorited to {illust_id}, file removed.")
    os.remove(full_path)


def __check_danbooru(full_path:str, file_name:str) -> bool:
    """Checks file for source/MD5 match on Danbooru."""

    params = {}
    with open(full_path, "rb") as file:
        # NOTE: {"md5": f"{img_md5}"} <- DON'T USE. This is a very iffy tag, it only supplies 1 result if found and 
        # if nothing is found it gives a 404 error. "tags" param is safer as if it finds nothing it returns empty.
        params = {"tags": f"md5:{hashlib.md5(file.read()).hexdigest()}"}
    
    json_data = danAPI.get_posts(params)
    if any(json_data):
        for item in json_data:
            __add_favorite(full_path, file_name, item["id"])
        return True
    
    return False


def __process_results(full_path, file_name, response, threshold, db_bitmask:int) -> list[Result]:
    """summary: Extract file data and send to saucenao REST API. Log low similarity results to {log_name} for later use.

    Args:
        file_path (str): Full path to locate the file name.
        fname (str): Just the name of the file.
        threshold (int): Minimum threshold to detect if an image matches.
        db_bitmask (int): Flags set that will pull from certain websites in request.
        log_name (str): Name of the log file.
    """
    image_uid = None
    found = False
    for r in response["results"]:
        result = Result(db_bitmask, r)
        if result.header.similarity >= threshold:
            found = True
            # 93 and above are safe bets that the images are exactly the same (sans possible resolution differences)
            if result.header.similarity > 93:
                try:
                    __add_favorite(full_path, file_name, result.data.dan_id, result.header.similarity)
                    break
                except Exception as e:
                    image_uid = insert_result(full_path, saucenao.API.DBMask.index_danbooru, result.data.dan_id, result.header.similarity, found, image_uid)
                    raise Exception(f"""Failed to connect to Danbooru's API: {e}\n
                                    {file_name} added to database but will need to be manually reviewed via 'check-results'.\n
                                    Check that you have your Danbooru username/API Key as env variables.
                                    If using a VPN this could be causing 403 errors.""")
            # Anything lower will need to be double checked via 'check-results'.
            else:
                image_uid = insert_result(full_path, saucenao.API.DBMask.index_danbooru, result.data.dan_id, result.header.similarity, found, image_uid)
                print(f"{file_name} didn't meet similarity quota: {result.header.similarity}%, added record.")
    if not found:
        insert_result(full_path, 0, 0, 0, found)
        print(f"No results found for {file_name}.")

def add_to_danbooru(directory:str, recursive:bool, threshold:int, schedule:bool, hash_only:bool):
    db_bitmask = int(saucenao.API.DBMask.index_danbooru)
    sauceAPI = saucenao.API(db_bitmask, threshold)

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
            # Try to save a search by checking Danbooru first. Saucenao's API has a 100 search limit, Dan's doesn't, so doesn't hurt to check.
            if not __check_danbooru(full_path, file_name) and not hash_only:
                api_response = sauceAPI.send_request(full_path)
                if any(api_response) and int(api_response['header']['results_returned']) > 0:
                    short_remaining = api_response["header"]["short_remaining"]
                    long_remaining = api_response["header"]["long_remaining"]
                    print(f"Remaining Searches 30s|24h: {short_remaining}|{long_remaining}")

                    __process_results(full_path, file_name, api_response, threshold, db_bitmask)

                    # Check remaining searches.
                    if long_remaining <= 0:
                        print("Reached daily search limit, unable to process more request at this time.")
                        break
                    elif short_remaining <= 0:
                        print('Out of searches for this 30 second period. Sleeping for 25 seconds...')
                        time.sleep(25)
                else:
                    insert_result(full_path, 0, 0, 0)
                    print(f"No results found for {file_name}.")
        # If we've gotten through all files, write a log record to indication as such.
        else:
            msg = f"All files scanned for {directory}"
            name = "saucenao_completed"
            write_to_log(msg, name)
    except Exception as e:
        error_msg = (str(e))
        name = "saucenao_error"
        write_to_log(error_msg, name)
        print(f"{Fore.RED}ERROR: {error_msg}{Style.RESET_ALL}")

    # Once finished, set the crontab job to the ending time, this way there will be ample time to refresh the usages.
    if schedule:
        updateschedule.update_crontab_job(directory)