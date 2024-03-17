import src.database.imgdatabase as imgdatabase


def get_results(image_uid, similiarity):
    results_query = """SELECT * FROM Saucenao_Results 
       WHERE 
        image_uid = ? AND 
        similarity >= ? AND
        status = 0
    """
    return imgdatabase.db_handler.execute_query(results_query, [image_uid, similiarity])



def insert_result(image_uid:int, site_flag:int, illust_id:int, similarity:float):
    rst_qry, rst_params = ("INSERT INTO Saucenao_Results (image_uid, site_flag, site_id, similarity, status) VALUES (?, ?, ?, ?, 0);", 
                           [image_uid, site_flag, illust_id, similarity])
    imgdatabase.db_handler.execute_change(rst_qry, rst_params)


def update_results_status(results:list[int]):
    imgdatabase.db_handler.execute_change(f"UPDATE Saucenao_Results SET status = 1 WHERE result_uid IN ({','.join('?' for _ in results)})", results)
