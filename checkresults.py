import os
import sys
import webbrowser
import imgdatabase
from imgdatabase import Image, Saucenao_Result
import saucenaoconfig
from colorama import Fore, Style

if sys.platform == "linux":
    sys.path.append(os.path.expanduser("~/pCloudDrive/repos/DanbooruAPI/"))
elif sys.platform == "win32":
    sys.path.append("P:/repos/DanbooruAPI/")

import danbooru

danAPI = danbooru.API()
config = saucenaoconfig.config()
imgDB = imgdatabase.database()

results_query = """
   SELECT * FROM Saucenao_Results 
   WHERE 
    image_uid = ? AND 
    similarity >= ? AND
    status = 0
"""


def remove_file(image_uid:int):
    imgDB.execute_change("DELETE FROM Images WHERE image_uid = ?", [image_uid])


def update_status(result_uid:str):
    imgDB.execute_change("UPDATE Saucenao_Results SET status = 1 WHERE result_uid in (?)", [result_uid])


def display_results(image:Image, results:list[Saucenao_Result]):
    webbrowser.get(config.settings["DEFAULT_BROWSER"]).open(image.full_path, new = 0)

    for i in range(0, len(results)):
        result = results[i]
        print(f"{Fore.LIGHTMAGENTA_EX}{result.site_id} ({result.similarity}%) [{i}] {Fore.LIGHTMAGENTA_EX}{Style.RESET_ALL}")
        webbrowser.get(config.settings["DEFAULT_BROWSER"]).open(f"{danAPI.hostname}/posts/{result.site_id}", new = 2)

    try:
        while True:
            input_val = input(f"Enter result(s) that match separated by ','. (n - none/q - quit): ").lower()
            match input_val:
                case "n":
                    ids = [str(r.result_uid) for r in results]
                    update_status(",".join(ids))
                    break
                case "q":
                    print("Exited.")
                    exit()
                case _:
                    try:
                        for i in [int(i.strip()) for i in input_val.split(",")]:
                            dan_id = results[i].site_id
                            danAPI.add_favorite(dan_id)
                            print(f"{dan_id} added to favorites.")
                        remove_file(image.image_uid)
                        break
                    except:
                        print("Invalid input.")
    except Exception as e:
        print(e)


def check_low_threshold_results(threshold:float):
    try:
        image_list:list[Image] = [Image(r) for r in imgDB.execute_query("""SELECT * FROM Images""")]
        for i in image_list:
            if not os.path.exists(i.full_path):
                remove_file(i.image_uid)
                print(f"{i.file_name} already deleted. Removed entry.")
                continue

            results_list = [Saucenao_Result(r) for r in imgDB.execute_query(results_query, [i.image_uid, threshold])]
            if any(results_list):
                print(f"{Fore.LIGHTGREEN_EX}{i.file_name+i.ext} {Fore.LIGHTMAGENTA_EX}{Style.RESET_ALL}")
                display_results(i, results_list)

    except Exception as e:
        print(e)

    print("Done.")