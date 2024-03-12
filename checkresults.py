import os
import sys
import webbrowser
import imgdatabase
import saucenaoconfig
from colorama import Fore, Style

if sys.platform == "linux":
    sys.path.append(os.path.expanduser("~/pCloudDrive/repos/DanbooruAPI/"))
elif sys.platform == "win32":
    sys.path.append("P:/repos/DanbooruAPI/")

import danbooru

config = saucenaoconfig.config()
imgDB = imgdatabase.database()


def remove_file(image_uid):
    imgDB.execute_change("DELETE FROM Images WHERE image_uid = ?", [image_uid])


def update_status(result_uid):
    imgDB.execute_change("UPDATE Saucenao_Results SET status = 1 WHERE result_uid = ?", [result_uid])


def check_low_threshold_results(threshold:float, force:bool):
    # NOTE: The main importance of the log file is to ensure that we skip already searched files when running add_to_danbooru.
    # This is just a glorfied double check to make sure anything that didn't meet the threshold the first time wasn't a miss. 
    # At the same time, this can get overwhelmning the more files added to the log, so we need a way to establish if a file has or
    # has not been checked before, so at the end of the record it has a status code, which is as follows:
    #   u: Unknown, hasn't been checked before. These will always get checked when running this command (if it meets the specified threshold).
    #   n: No match, the files have been manually reviewed and confirmed not to match. Will not show up again unless -f is ran.
    # There is no need for a "matched" status code because if the file matches the record and file will both get removed.
    exit_loop = False
    
    # Need to split these two up, adding a index to the latter to be able to make changes to the log file.
    try:
        danAPI = danbooru.API()
        image_list = imgDB.execute_query(""" SELECT * FROM Images""")
        for image_uid, file_name, full_path, ext in image_list:
            results_list = imgDB.execute_query("""
                   SELECT * FROM Saucenao_Results 
                   WHERE 
                    image_uid = ? AND 
                    similarity >= ? AND
                    status = 0
            """, [image_uid, threshold])
            for result_uid, _, site_id, img_id, sim, status in results_list:
                if not os.path.exists(full_path):
                    remove_file(full_path)
                    print(f"{file_name} already deleted. Removed entry.")
                    continue
                
                print(f"{Fore.LIGHTGREEN_EX}{file_name+ext} {Fore.LIGHTMAGENTA_EX}({sim}%){Style.RESET_ALL}")
                webbrowser.get(config.settings["DEFAULT_BROWSER"]).open(f"{danAPI.hostname}/posts/{img_id}", new = 0)
                webbrowser.get(config.settings["DEFAULT_BROWSER"]).open(full_path, new = 2)

                # Why does python not have a do while? Forcing breaks is stupid.
                removed = False
                try:
                    while True:
                        input_val = input(f"Do the files match? (y/n/q): ").lower()
                        match input_val:
                            case "y":
                                removed = True
                                danAPI.add_favorite(img_id)
                                remove_file(image_uid)
                                os.remove(full_path)
                                print("Added to favorites and removed file.")
                                break
                            case "n":
                                update_status(result_uid)
                                break
                            case "q":
                                print("Exited.")
                                return
                            case _:
                                print("Invalid input.")
                except Exception as e:
                    print(e)
                if removed:
                    break
    except Exception as e:
        print(e)

    print("Done.")