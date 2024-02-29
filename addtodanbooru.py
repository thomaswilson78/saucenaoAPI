import os
import sys
import time
import hashlib
import saucenao
import saucenaolog
from colorama import Fore, Style

if sys.platform == "linux":
    sys.path.append(os.path.expanduser("~/pCloudDrive/repos/DanbooruAPI/"))
elif sys.platform == "win32":
    sys.path.append("P:/repos/DanbooruAPI/")

import danbooru

danAPI = danbooru.API()


def __add_favorite(file_path:str, fname:str, illust_id:int, similarity:int = None):
    danAPI.add_favorite(illust_id)
    if similarity is None:
        print(f"Match found (via danbooru): {fname} favorited to {illust_id}, file removed.")
    else:
        print(f"Match found ({similarity}%): {fname} favorited to {illust_id}, file removed.")
    os.remove(file_path)


def __check_danbooru(file_path:str, fname:str) -> bool:
    """Checks file for source/MD5 match."""
    # Naming schema when saving via webimageextractor.py. While that app automatically checks Danbooru for the tweet ID, 
    # it's possible the image was too new and wasn't uploaded yet.
    if fname.find(" - "):
        for f in fname.split(" - "):
            if str.isnumeric(f):
                json_data = danAPI.get_posts({"tags": f"source:*twitter.com*{f}"})
                if any(json_data):
                    for item in json_data:
                        __add_favorite(file_path, fname, item["id"])
                    return True
    else:
        params = {}
        # Danbooru images save with "__" at the beginning so we can pull the md5 from the end of the filename
        if fname.startswith("__"):
            img_md5 = fname[fname.rfind("_"):]
            params = {"tags": f"md5:{img_md5}"}
        # Get the MD5 value from the image itself
        else:
            # Open,close, read file and calculate MD5 on its contents 
            with open(file_path, 'rb') as file_to_check:
                # read contents of the file
                data = file_to_check.read()    
                # pipe contents of the file through
                img_md5 = hashlib.md5(data).hexdigest()
                params = {"tags": f"md5:{img_md5}"}
        
        json_data = danAPI.get_posts(params)
        if any(json_data):
            for item in json_data:
                __add_favorite(file_path, fname, item["id"])
            return True
    
    return False


def __process_file(file_path:str, fname:str, threshold:int, db_bitmask:int, log_only:bool, log_name:str):
    """summary: Extract file data and send to saucenao REST API. Log low similarity results to \"saucenao_log.txt\" for later use.

    Args:
        file_path (str): Full path to locate the file name.
        fname (str): Just the name of the file.
        threshold (int): Minimum threshold to detect if an image matches.
        db_bitmask (int): Flags set that will pull from certain websites in request.
        log_only (bool): Only add files to log file, does not add to Danbooru.
        log_name (str): Name of the log file.
    """
    sauAPI = saucenao.API(db_bitmask, threshold)
    results = sauAPI.send_request(file_path)
    
    if any(results):
        if int(results['header']['results_returned']) > 0:
            #one or more results were returned
            similarity = float(results['results'][0]['header']['similarity'])
            illust_id = 0

            try:
                if db_bitmask & int(sauAPI.DBMask.index_danbooru) > 0:
                    illust_id=results['results'][0]['data']['danbooru_id']
                    
                    if log_only:
                        saucenaolog.append_log(log_name, f"{similarity},{fname},{illust_id},u\n")
                        print(f"{file_path} : {similarity}% - added to log.")

                    # 90% practically never has issues, so it should be fine to add the image as a favorite and remove it.
                    # When you run into anything below that though, it gets a bit troublesome, so instead of fretting over it,
                    # we can log the result and then check them later.
                    if similarity > 90:
                        if illust_id > 0:
                            try:
                                __add_favorite(file_path, fname, illust_id, similarity)
                            except Exception as e:
                                # If Danbooru is refusing connections end this process. Otherwise it'll just waste time.
                                saucenaolog.append_log(log_name, f"{similarity},{fname},{illust_id},u\n")
                                print(f"{Fore.RED}Failed to connect to Danbooru's API: {e}{Style.RESET_ALL}")
                                print(f"{Fore.RED}{fname} added to log but will need to be manually reviewed.{Style.RESET_ALL}")
                                print(f"{Fore.RED}Check that you have your Danbooru username/API Key as env variables. If using a VPN this could be causing 403 errors.{Style.RESET_ALL}")
                                exit(1)
                    else:
                        print(f"{fname} didn't meet similarity quota: {similarity}%, added to log.")
                        saucenaolog.append_log(log_name, f"{similarity},{file_path},{illust_id},u\n")
            except Exception as e:
                print(e)
        else:
            print(f"No results found for {fname}")
            # Even if nothing is found, we still need to update the log file to ensure the file won't be checked again
            saucenaolog.append_log(log_name, f"0,{file_path},0,u\n")

        if int(results['header']['long_remaining'])<1: #could potentially be negative
            print("Reached daily search limit, unable to process more request at this time.")
            sys.exit()
        if int(results['header']['short_remaining'])<1:
            print('Out of searches for this 30 second period. Sleeping for 25 seconds...')
            time.sleep(25)

def add_to_danbooru(file:str, directory:str, recursive:bool, threshold:int, log_only:bool, log_name):
    already_searched = saucenaolog.searched_files(log_name) 
    # Generate appropriate bitmask
    db_bitmask = int(saucenao.API.DBMask.index_danbooru)
    all_files: list[str] = []

    # Setup list of files to be searched
    if not file is None:
        all_files.append(file)
    else:
        if recursive: 
            all_files = [os.path.join(dirpath, f) for dirpath, _, files in os.walk(directory) for f in files]
        else:
            all_files = os.listdir(directory)
    
    for file in all_files:
        # Just to make sure we don't waste precious searches
        if saucenaolog.skip_file(file, already_searched):
            continue

        fname = os.path.split(file)[1]
        # Before we send to saucenao, just double check the file doesn't already contain the source or MD5 value.
        if not __check_danbooru(file, fname):
            __process_file(file, fname, threshold, db_bitmask, log_only, log_name)