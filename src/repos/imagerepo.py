import os
import src.repos.repohelper as repohelper
import src.database.imgdatabase as imgdatabase
from src.database.imgdatabase import Parameter
from src.modules.imgmodule import Image
from enum import IntEnum


class image_status(IntEnum):
    full_scan = 1
    md5_only_scan = 2
    banned_artist = 3
    
    
def get_images(params:list[Parameter] = ()) -> list[Image]:
    query, param_list = repohelper.get_where("SELECT * FROM Images WHERE 1=1", params)

    results = imgdatabase.db_handler.execute_query(query, param_list)
    image_list = [Image(dr) for dr in results]
    
    return image_list


def update_image(update_params:list[Parameter], where_params:list[Parameter]):
    query = f"UPDATE Images SET {','.join(f'{p.col_name} = ?' for p in update_params)}"
    param_list = [p.value for p in update_params]
    where_set = repohelper.get_where(" WHERE 1=1", where_params)
    query += where_set[0]
    param_list.extend(where_set[1])
    imgdatabase.db_handler.execute_change(query, param_list)


#def update_image(image_uid, file_name, full_path, status):
#    file = os.path.splitext(file_name)[0]
#    imgdatabase.db_handler.execute_change("UPDATE Images SET file_name=?, full_path=?, status=? WHERE image_uid=?", [file, full_path, status, image_uid])


def delete_image(image_uid):
    imgdatabase.db_handler.execute_change("DELETE FROM Images WHERE image_uid=?", [image_uid])


def insert_image(full_path:str, md5:str, status:image_status = image_status.full_scan) -> int | None:
    file_name, ext = os.path.splitext(os.path.split(full_path)[1])
    img_qry, img_params = ("INSERT INTO Images (full_path, file_name, ext, md5, status) VALUES (?, ?, ?, ?, ?);", [full_path, file_name, ext, md5, status])
    return imgdatabase.db_handler.execute_change(img_qry, img_params)


def check_existing_file(full_path, md5):
    """Check the MD5 value to ensure the file hasn't been moved, renamed, or is a duplicate."""
    response = {"status": 0, "msg": None} 
    images = get_images([Parameter("md5", md5)])
    if any(images):
        file_name = os.path.splitext(os.path.basename(full_path))[0]
        image = images[0]
        # If the file doesn't match the full path then either it's been changed or is a dupe
        if full_path != image.full_path:
            # Original still exists confirming this is a dupe.
            if os.path.exists(image.full_path):
                response["status"] = 1 
                response["msg"] = f"{full_path} is a duplicate file. File with same MD5 already exists: {image.full_path}" 
            # Otherwise the file has been moved or renamed, update the database to reflect.
            else:
                response["status"] = 2 
                response["msg"] = f"{full_path} has been moved/renamed. Updated database to reflect change." 
                update_image(image.image_uid, file_name, full_path)
                
    return response