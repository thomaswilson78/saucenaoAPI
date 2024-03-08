import os
import sys
import webbrowser
import saucenaoconfig
from colorama import Fore, Style

if sys.platform == "linux":
    sys.path.append(os.path.expanduser("~/pCloudDrive/repos/DanbooruAPI/"))
elif sys.platform == "win32":
    sys.path.append("P:/repos/DanbooruAPI/")

import danbooru

config = saucenaoconfig.config()


def append_log(log_name, line:str):
    write_log(log_name, [line], "+a")


def write_log(log_name, lines:list[str], permission:str):
    with open(log_name, permission) as f:
        f.writelines(lines)


def extract_log(log_name) -> list[str]:
    """Pull records from log file."""
    if os.path.exists(log_name):
        with open(log_name) as f:
            return f.readlines()


def searched_files(log_name) -> set[str]:
    # already_searched is global so we only have to pull once without passing data.
    already_searched = set()
    """Pull list of files that have already been searched before from the log file."""
    for l in extract_log(log_name):
        fname = l.split(",")[1]
        already_searched.add(fname)
        
    return already_searched


def check_log(threshold:float, force:bool, log_name:str):
    # NOTE: The main importance of the log file is to ensure that we skip already searched files when running add_to_danbooru.
    # This is just a glorfied double check to make sure anything that didn't meet the threshold the first time wasn't a miss. 
    # At the same time, this can get overwhelmning the more files added to the log, so we need a way to establish if a file has or
    # has not been checked before, so at the end of the record it has a status code, which is as follows:
    #   u: Unknown, hasn't been checked before. These will always get checked when running this command (if it meets the specified threshold).
    #   n: No match, the files have been manually reviewed and confirmed not to match. Will not show up again unless -f is ran.
    # There is no need for a "matched" status code because if the file matches the record and file will both get removed.
    exit_loop = False
    changes = False
    
    # Need to split these two up, adding a index to the latter to be able to make changes to the log file.
    log_files = extract_log(log_name)
    file_list = [ (str(x) + "," + log_files[x]).split(",") for x in range(0, len(log_files)) ]

    # Do this in reverse, this way items can be removed without risk of messing up sequence
    try:
        danAPI = danbooru.API()
        for i, sim, fname, ill_id, status in reversed(file_list):
            if exit_loop:
                break

            idx = int(i)

            if float(sim) < threshold:
                continue
            elif status[0] == "n" and not force:
                continue
            elif not os.path.exists(fname):
                changes = True
                log_files.pop(idx)
                print(f"{fname} already deleted. Removed from log.")
                continue
            
            name = os.path.split(fname)[1]
            print(f"{Fore.LIGHTGREEN_EX}{name} {Fore.LIGHTMAGENTA_EX}({sim}%){Style.RESET_ALL}")
            webbrowser.get(config.settings["DEFAULT_BROWSER"]).open(f"{danAPI.hostname}/posts/{ill_id}", new = 0)
            webbrowser.get(config.settings["DEFAULT_BROWSER"]).open(fname, new = 2)

            # Why does python not have a do while? Forcing breaks is stupid.
            try:
                while True:
                    input_val = input(f"Do the files match? (y/n/q): ").lower()
                    match input_val:
                        case "y":
                            changes = True
                            log_files.pop(idx)
                            danAPI.add_favorite(ill_id)
                            os.remove(fname)
                            print("Added to favorites and removed file.")
                            break
                        case "n":
                            changes = True
                            log_files[idx] = log_files[idx].replace(",u\n", ",n\n")
                            break
                        case "q":
                            exit_loop = True
                            break
                        case _:
                            print("Invalid input.")
            except Exception as e:
                print(e)
    except Exception as e:
        print(e)

    # Ensure that we update the log file with any changes made.
    if changes:
        write_log(log_name, log_files, "+w")
    
    print("Done.")
    
    