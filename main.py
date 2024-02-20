#!/usr/bin/env python -u
import sys
import os
import json
import codecs
import time
import click
import webbrowser
import saucenao
from PIL import Image

if sys.platform == "linux":
    sys.path.append(os.path.expanduser("~/pCloudDrive/repos/DanbooruAPI/"))
elif sys.platform == "win32":
    sys.path.append("P:/repos/DanbooruAPI/")

import danbooruapi

__LOG_NAME="./saucenao_log.txt"
__CONFIG_FILE="./config.json"

sys.stdout = codecs.getwriter('utf8')(sys.stdout.detach())
sys.stderr = codecs.getwriter('utf8')(sys.stderr.detach())

config = {}
already_searched: list[str] = []
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


#########EXPAND CLICK FUNCTIONALITY##########

class Mutex(click.Option):
    def __init__(self, *args, **kwargs):
        self.not_required_if:list = kwargs.pop("not_required_if")

        assert self.not_required_if, "'not_required_if' parameter required"
        kwargs["help"] = (kwargs.get("help", "") + " Option can be interchanged with \"--" + "".join(self.not_required_if) + "\".").strip()
        super(Mutex, self).__init__(*args, **kwargs)

    def handle_parse_result(self, ctx, opts, args):
        current_opt:bool = self.name in opts
        for mutex_opt in self.not_required_if:
            if mutex_opt in opts:
                if current_opt:
                    raise click.UsageError("Illegal usage: '" + str(self.name) + "' is mutually exclusive with " + str(mutex_opt) + ".")
                else:
                    self.prompt = None
        return super(Mutex, self).handle_parse_result(ctx, opts, args)

#####################END#####################

@click.group()
def commands():
    pass


def load_config():
    global config
    # If there's no default config file, create it.
    if not os.path.exists(__CONFIG_FILE):
        config = {
            "DEFAULT_BROWSER": "firefox"
        }
        json.dump(config, open(__CONFIG_FILE, "w"))
    else:
        config = json.load(open(__CONFIG_FILE))
        

def append_log(line:str):
    write_log([line], "+a")


def write_log(lines:list[str], permission:str):
    with open(__LOG_NAME, permission) as f:
        f.writelines(lines)


def extract_log():
    """Pull records from log file."""
    if os.path.exists(__LOG_NAME):
        with open(__LOG_NAME) as f:
            return f.readlines()


def searched_files():
    """Pull list of files that have already been searched before from the log file."""
    extract_log()
    for l in extract_log():
        fname = l.split(",")[1]
        already_searched.append(fname)


def skip_file(fname: str):
    """Skip files that have already been searched before, not of a valid extension, or has blacklisted terms (mainly for AI art)."""
    if not os.path.isfile(fname):
        return True
    elif fname in already_searched:
        return True
    elif not os.path.splitext(fname)[1] in saucenao.API.get_allowed_extensions():
        return True
    elif any(bl in fname for bl in blacklisted_terms):
        return True
    
    return False


def process_file(fname: str, threshold:int, db_bitmask: int):
    """Extract file data and send to saucenao REST API. Log low similarity results to \"saucenao_log.txt\" for later use."""
    file = os.path.split(fname)[1]
    API = saucenao.API(db_bitmask, threshold)

    results = API.send_request(fname)
    
    if any(results):
        if int(results['header']['results_returned']) > 0:
            #one or more results were returned
            similarity = float(results['results'][0]['header']['similarity'])
            illust_id = 0

            try:
                if db_bitmask & int(API.DBMask.index_danbooru) > 0:
                    illust_id=results['results'][0]['data']['danbooru_id']

                    # 90% practically never has issues, so it should be fine to add the image as a favorite and remove it.
                    # When you run into anything below that though, it gets a bit troublesome, so instead of fretting over it,
                    # we can log the result and then check them later.
                    if similarity > 90:
                        if illust_id > 0:
                            danbooruapi.API.add_favorite(illust_id)
                            print(f"Match found ({similarity}%): {file} favorited to {illust_id}, file removed.")
                            os.remove(fname)
                    else:
                        print(f"{file} didn't meet similarity quota: {similarity}%, added to log.")
                        append_log(f"{similarity},{fname},{illust_id},u\n")
            except Exception as e:
                print(e)
        else:
            print(f"No results found for {file}")
            # Even if nothing is found, we still need to update the log file to ensure the file won't be checked again
            append_log(f"0,{fname},0,u\n")

        if int(results['header']['long_remaining'])<1: #could potentially be negative
            print("Reached daily search limit, unable to process more request at this time.")
            sys.exit()
        if int(results['header']['short_remaining'])<1:
            print('Out of searches for this 30 second period. Sleeping for 25 seconds...')
            time.sleep(25)


@click.command()
@click.option("-t", "--threshold", type=click.FLOAT, default=80, show_default=True, 
              help="Compare files above minimum similarity threshold.")
@click.option("-f", "--force", is_flag=True, show_default=True, default=False, 
              help="Force all files to be compared, even those that have been previously checked.")
def check_log(threshold, force):
    """
    Allow manual review of files added to the log file, determined by the minimum threshold.
    Opens a browser window with two tabs, one for Danbooru the other for the file stored locally.
    If determined they matched, will favorite on Danbooru and remove the file & log record.
    """
    # NOTE: The main importance of the log file is to ensure that we skip already searched files when running add_to_danbooru.
    # This is just a glorfied double check to make sure anything that didn't meet the threshold the first time wasn't a miss. 
    # At the same time, this can get overwhelmning the more files added to the log, so we need a way to establsih if a file has or
    # has not been checked before, so at the end of the record it has a status code, which is as follows:
    #   u: Unknown, hasn't been checked before. These will always get checked when running this command (if it meets the specified threshold).
    #   n: No match, the files have been manually reviewed and confirmed not to match. Will not show up again unless -f is ran.
    # There is no need for a "matched" status code because if the file matches the record and file will both get removed.
    exit_loop = False
    changes = False
    
    # Need to split these two up, adding a index to the latter to be able to make changes to the log file.
    log_files = extract_log()
    file_list = [ (str(x) + "," + log_files[x]).split(",") for x in range(0, len(log_files)) ]

    # Do this in reverse, this way items can be removed without risk of messing up sequence
    for i, sim, fname, ill_id, status in reversed(file_list):
        try:
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
            
            webbrowser.get(config["DEFAULT_BROWSER"]).open(f"{danbooruapi.hostname}/posts/{ill_id}", new = 0)
            webbrowser.get(config["DEFAULT_BROWSER"]).open(fname, new = 2)

            # Why does python not have a do while? Forcing breaks is stupid.
            try:
                while True:
                    input_val = input("Do the files match? (y/n/q): ").lower()
                    match input_val:
                        case "y":
                            changes = True
                            log_files.pop(idx)
                            danbooruapi.API.add_favorite(ill_id)
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
        write_log(log_files, "+w")
    
    print("Done.")


@click.command()
@click.argument("-d", "--directory", 
                type=click.Path(exists=True, file_okay=False), 
                cls=Mutex, not_required_if='file', 
                help="Directory to pull images from.")
@click.argument("-f", "--file", 
                type=click.Path(exists=True, dir_okay=False), 
                cls=Mutex, not_required_if='directory', 
                help="Image to check.")
@click.option("-r", "--recursive", 
              is_flag=True, show_default=True, default=False, 
              help="Pull images from all sub-directories within specified directory.")
@click.option("-t", "--threshold", type=int, default=0, show_default=True, 
              help="Compare files above minimum similarity threshold.")
def add_to_danbooru(file:str, directory:str, recursive:bool, threshold:int):
    """
    Connects to the Saucenao web API to look at specified file(s) and determine if they match. If they match, will favorite the image
    on Danbooru then remove the file from the local machine.
    """
    searched_files()
    # Generate appropriate bitmask
    db_bitmask = int(saucenao.API.DBMask.index_danbooru)
    all_files: list[str] = []

    # Setup list of files to be searched
    if not file is None:
        all_files.append(file)
    else:
        if recursive: 
            for dirpath, _, files in os.walk(directory):
                for f in files:
                    all_files.append(os.path.join(dirpath, f))
        else:
            all_files = os.listdir(directory)
    
    for fname in all_files:
        # Just to make sure we don't waste precious searches
        if skip_file(fname):
            continue
        process_file(fname, threshold, db_bitmask)


commands.add_command(check_log)
commands.add_command(add_to_danbooru)


if __name__ == "__main__":
    load_config()
    commands()
