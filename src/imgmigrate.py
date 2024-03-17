# Originally I just downloaded the files manually which only gives the twitter image ID for the file name. But after creating the new naming schema that
# also has the artist and status, I felt like I needed to cleanup some files that aren't properly named. However, the only way to do that is to
# reverse image search and find/re-download those files with the image extractor to ensure they're named properly. This tool will make it simple by
# cross-referencing the image that only has the image ID with the properly named image in "_Needs Sorted" and not only renamed itself properly, but also
# update the Images table with the new name (for both file_name and full_path).

import os
import sys
import src.repos.imagerepo as imagerepo
from src.modules.imgmodules import Image

__pcloud_path = ""

if sys.platform == "linux":
    __pcloud_path = os.path.expanduser("~/pCloudDrive/")
elif sys.platform == "win32":
    __pcloud_path = "P:/"

    
def migrate_files(dir):
    """Check file names and rename file with new naming schema."""
    image_ids:dict[str:str] = {f"{f.split(' - ')[2]}": f"{f}" for f in os.listdir("/home/afrodown/pCloudDrive/Images/_Need Sorted")}

    unsourced_files = {f"{dir}/{f}": f"{os.path.split(f)[1]}" for dir, _, files in os.walk(dir) for f in files}

    for full_path, file_name in unsourced_files.items():
        path, file_name = os.path.split(full_path)
        if file_name in image_ids:
            sourced_name = os.path.split(image_ids[file_name])[1]
            new_full_path = f"{path}/{sourced_name}"
            data = imagerepo.search_by_full_path(full_path)
            if any(data):
                image = Image(data[0])
                imagerepo.update_image(image.image_uid, sourced_name, new_full_path)
            os.rename(full_path, new_full_path)
            os.remove("/home/afrodown/pCloudDrive/Images/_Need Sorted/" + image_ids[file_name])