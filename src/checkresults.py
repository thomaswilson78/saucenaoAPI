import os
import sys
import webbrowser
from colorama import Fore, Style
from src.modules.imgmodules import Image, Saucenao_Result
import src.repos.imagerepo as imagerepo
import src.repos.saucenaoresultrepo as saucenaoresultrepo
import src.saucenaoconfig as saucenaoconfig

if sys.platform == "linux":
    sys.path.append(os.path.expanduser("~/pCloudDrive/repos/DanbooruAPI/"))
elif sys.platform == "win32":
    sys.path.append("P:/repos/DanbooruAPI/")

import danbooru

danAPI = danbooru.API()
config = saucenaoconfig.config



def remove_file(image:Image):
    imagerepo.delete_image(int(image.image_uid))
    if os.path.exists(image.full_path):
        os.remove(image.full_path)


def add_favorite(img_id):
    danAPI.add_favorite(img_id)
    print(f"{img_id} added to favorites.")

def display_results(image:Image, results:list[Saucenao_Result]):
    webbrowser.get(config.settings["DEFAULT_BROWSER"]).open(image.full_path, new = 0)

    for i in range(0, len(results)):
        result = results[i]
        print(f"{Fore.LIGHTMAGENTA_EX}{result.site_id} ({result.similarity}%) [{i}] {Fore.LIGHTMAGENTA_EX}{Style.RESET_ALL}")
        webbrowser.get(config.settings["DEFAULT_BROWSER"]).open(f"{danAPI.hostname}/posts/{result.site_id}", new = 2)

    try:
        while True:
            input_val = input(f"Enter result(s) that match separated by ','. (a - all/n - none): ").lower()
            match input_val:
                case "n":
                    saucenaoresultrepo.update_results_status([r.result_uid for r in results])
                    break
                case "a":
                    for r in results:
                        add_favorite(r.site_id)
                    remove_file(image)
                    break
                case _:
                    try:
                        for i in [int(i.strip()) for i in input_val.split(",")]:
                            add_favorite(results[i].site_id)
                        remove_file(image)
                        break
                    except:
                        print("Invalid input.")
    except Exception as e:
        print(e)


def check_low_threshold_results(threshold:float):
    try:
        image_list:list[Image] = [Image(r) for r in imagerepo.get_images()]
        for i in image_list:
            if not os.path.exists(i.full_path):
                remove_file(i)
                print(f"{i.file_name} already deleted. Removed entry.")
                continue

            results_list = [Saucenao_Result(r) for r in saucenaoresultrepo.get_results(i.image_uid, threshold)]
            if any(results_list):
                print(f"{Fore.LIGHTGREEN_EX}{i.file_name+i.ext} {Fore.LIGHTMAGENTA_EX}{Style.RESET_ALL}")
                display_results(i, results_list)

    except Exception as e:
        print(e)

    print("Done.")