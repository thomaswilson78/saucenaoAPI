class Image:
    def __init__(self, datarow):
        self.image_uid = datarow[0]
        self.file_name = datarow[1]
        self.full_path = datarow[2]
        self.ext = datarow[3]

class Saucenao_Result:
    def __init__(self, datarow):
        self.result_uid = datarow[0]
        self.image_uid = datarow[1]
        self.site_flag = datarow[2]
        self.site_id = datarow[3]
        self.similarity = datarow[4]
        self.status = datarow[5]
