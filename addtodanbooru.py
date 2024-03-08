import os
import sys
import time
import hashlib
import datetime
import saucenao
import saucenaolog
import updateschedule
from colorama import Fore, Style

if sys.platform == "linux":
    sys.path.append(os.path.expanduser("~/pCloudDrive/repos/DanbooruAPI/"))
elif sys.platform == "win32":
    sys.path.append("P:/repos/DanbooruAPI/")

import danbooru

danAPI = danbooru.API()


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


def skip_file(fname:str, already_searched:set[str]):
    """Skip non-files, files that have already been searched before, not of a valid extension, or has blacklisted terms (mainly for AI art)."""
    if not os.path.isfile(fname):
        return True
    elif fname in already_searched:
        return True
    elif not os.path.splitext(fname)[1] in saucenao.API.get_allowed_extensions():
        return True
    elif any(bl in fname for bl in blacklisted_terms):
        return True
    
    return False



def __add_favorite(file_path:str, fname:str, illust_id:int, similarity:int = None):
    danAPI.add_favorite(illust_id)
    if similarity is None:
        print(f"Match found (via danbooru): {fname} favorited to {illust_id}, file removed.")
    else:
        print(f"Match found ({similarity}%): {fname} favorited to {illust_id}, file removed.")
    os.remove(file_path)


def __check_danbooru(file_path:str, fname:str) -> bool:
    """Checks file for source/MD5 match."""

    params = {}
    with open(file_path, "rb") as file:
        # NOTE: {"md5": f"{img_md5}"} <- DON'T USE. This is a very iffy tag, it only supplies 1 result if found and 
        # if nothing is found it gives a 404 error. "tags" param is safer as if it finds nothing it returns empty.
        tags = f"md5:{hashlib.md5(file.read()).hexdigest()}"

        # Naming schema when saving via imgextract.py. While that app automatically checks Danbooru for the tweet ID, 
        # it's possible the image was too new and wasn't uploaded yet.
        if fname.find(" - "):
            for f in fname.split(" - "):
                if str.isnumeric(f):
                    tags += f" or source:*twitter.com*{f}"
                    break
        params = {"tags": f"{tags}"}
    
    json_data = danAPI.get_posts(params)
    if any(json_data):
        for item in json_data:
            __add_favorite(file_path, fname, item["id"])
        return True
    
    return False


def __process_file(file_path:str, fname:str, threshold:int, db_bitmask:int, log_name:str) -> bool:
    """summary: Extract file data and send to saucenao REST API. Log low similarity results to {log_name} for later use.

    Args:
        file_path (str): Full path to locate the file name.
        fname (str): Just the name of the file.
        threshold (int): Minimum threshold to detect if an image matches.
        db_bitmask (int): Flags set that will pull from certain websites in request.
        log_name (str): Name of the log file.
    """
    sauceAPI = saucenao.API(db_bitmask, threshold)
    results = sauceAPI.send_request(file_path)
    
    if any(results):
        if int(results['header']['results_returned']) > 0:
            print("Remaining Searches 30s|24h: "+str(results["header"]["short_remaining"])+"|"+str(results["header"]["long_remaining"]))
            #one or more results were returned
            similarity = float(results['results'][0]['header']['similarity'])

            if db_bitmask & int(sauceAPI.DBMask.index_danbooru) > 0:
                illust_id=results['results'][0]['data']['danbooru_id']
                
                # 90% practically never has issues, so it should be fine to add the image as a favorite and remove it.
                # When you run into anything below that though, it gets a bit troublesome, so instead of fretting over it,
                # we can log the result and then check them later.
                if similarity > 90:
                    if illust_id > 0:
                        try:
                            __add_favorite(file_path, fname, illust_id, similarity)
                        except Exception as e:
                            # If Danbooru is refusing connections end this process. Otherwise it'll just waste time.
                            saucenaolog.append_log(log_name, f"{similarity},{file_path},{illust_id},u\n")
                            raise Exception(f"""Failed to connect to Danbooru's API: {e}\n
                                            {fname} added to log but will need to be manually reviewed.\n
                                            Check that you have your Danbooru username/API Key as env variables.
                                            If using a VPN this could be causing 403 errors.""")
                else:
                    print(f"{fname} didn't meet similarity quota: {similarity}%, added to log.")
                    saucenaolog.append_log(log_name, f"{similarity},{file_path},{illust_id},u\n")
        else:
            print(f"No results found for {fname}")
            # Even if nothing is found, we still need to update the log file to ensure the file won't be checked again
            saucenaolog.append_log(log_name, f"0,{file_path},0,u\n")

        if int(results['header']['long_remaining'])<1: #could potentially be negative
            print("Reached daily search limit, unable to process more request at this time.")
            # Hit the daily limit, can no longer proceed
            return True
        if int(results['header']['short_remaining'])<1:
            print('Out of searches for this 30 second period. Sleeping for 25 seconds...')
            time.sleep(25)
    else:
        print(f"No results found for {fname}")

    return False

def add_to_danbooru(directory:str, recursive:bool, threshold:int, schedule:bool, hash_only:bool, log_name):
    already_searched = saucenaolog.searched_files(log_name) 
    # Generate appropriate bitmask
    db_bitmask = int(saucenao.API.DBMask.index_danbooru)
    all_files: list[str] = []

    # Setup list of files to be searched
    if recursive: 
        all_files = [os.path.join(dirpath, f) for dirpath, _, files in os.walk(directory) for f in files]
    else:
        all_files = os.listdir(directory)
    
    daily_limit = False
    try:
        for file in all_files:
            if skip_file(file, already_searched):
                continue

            fname = os.path.split(file)[1]
            # Before we send to saucenao, double check that we can't get the image from the source or MD5 value.
            # Since we're limited to 100 daily searches, they're rather precious so if we can save even one of them
            # it would be a huge help.
            db_found = __check_danbooru(file, fname)
            if not db_found and not hash_only:
                daily_limit = __process_file(file, fname, threshold, db_bitmask, log_name)
                if daily_limit:
                    break
    
    except Exception as e:
        error_msg = (str(e))
        dt = datetime.datetime.now()
        strdt = str(dt.date()) + "_" + str(dt.hour) + str(dt.minute)
        msg = strdt + "\n" + directory + '\n' + error_msg
        path = os.path.expanduser("~/Desktop/")
        saucenaolog.write_log(path + f"saucenao_error_{strdt}.log", msg, "w")
        print(f"{Fore.RED}Error: {error_msg}{Style.RESET_ALL}")

    # Once finished, set the crontab job to the ending time, this way there will be ample time to refresh the usages.
    if schedule:
        updateschedule.update_crontab_job(directory)