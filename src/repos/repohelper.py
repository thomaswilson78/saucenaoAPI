from src.database.imgdatabase import Parameter


def get_where(query:str, params:list[Parameter]):
    param_list = []
    for p in params:
        query += p.get_where()
        if type(p.value) is list:
            param_list.extend(p.value)
        else:
            param_list.append(p.value)
     
    return (query, param_list)