import src.repos.repohelper as repohelper
from src.modules.imgmodule import Saucenao_Result
from src.database.imgdatabase import Parameter
import src.database.imgdatabase as imgdatabase


def get_results(params:list[Parameter] = ()) -> list[Saucenao_Result]:
    query, param_list = repohelper.get_where("SELECT * FROM Saucenao_Results WHERE 1=1", params)

    results = imgdatabase.db_handler.execute_query(query, param_list)
    saucenao_result_list = [Saucenao_Result(dr) for dr in results]
    
    return saucenao_result_list


def insert_result(image_uid:int, site_flag:int, illust_id:int, similarity:float):
    rst_qry, rst_params = ("INSERT INTO Saucenao_Results (image_uid, site_flag, site_id, similarity, status) VALUES (?, ?, ?, ?, 0);", 
                           [image_uid, site_flag, illust_id, similarity])
    imgdatabase.db_handler.execute_change(rst_qry, rst_params)


def update_results(update_params:list[Parameter], where_params:list[Parameter]):
    query = f"UPDATE Saucenao_Results SET {','.join(f'{p.col_name} = ?' for p in update_params)}"
    param_list = [p.value for p in update_params]
    where_set = repohelper.get_where(" WHERE 1=1", where_params)
    query += where_set[0]
    param_list.extend(where_set[1])
    imgdatabase.db_handler.execute_change(query, param_list)
