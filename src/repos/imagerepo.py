import os
import src.database.imgdatabase as imgdatabase
from src.modules.imgmodules import Image


def get_images():
    return imgdatabase.db_handler.execute_query("SELECT * FROM Images")


def search_by_md5(md5):
    return imgdatabase.db_handler.execute_query("SELECT * FROM Images WHERE md5=?", [md5])


def search_by_full_path(full_path:str):
    return imgdatabase.db_handler.execute_query(f"SELECT image_uid FROM Images WHERE full_path=?", [full_path])


def update_image(image_uid, file_name, full_path):
    file = os.path.splitext(file_name)[0]
    imgdatabase.db_handler.execute_change("UPDATE Images SET file_name=?, full_path=? WHERE image_uid=?", [file, full_path, image_uid])


def delete_image(image_uid):
    imgdatabase.db_handler.execute_change("DELETE FROM Images WHERE image_uid=?", [image_uid])


def insert_image(full_path, md5):
    file_name, ext = os.path.splitext(os.path.split(full_path)[1])
    img_qry, img_params = ("INSERT INTO Images (full_path, file_name, ext, md5) VALUES (?, ?, ?, ?);", [full_path, file_name, ext, md5])
    return imgdatabase.db_handler.execute_change(img_qry, img_params)


def check_existing_file(md5, full_path):
    """Check the MD5 value to ensure the file hasn't been moved, renamed, or is a duplicate."""
    response = {"status": 0, "msg": None} 
    datarow = search_by_md5(md5)
    if any(datarow):
        file_name = os.path.splitext(os.path.basename(full_path))[0]
        image = Image(datarow[0])
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