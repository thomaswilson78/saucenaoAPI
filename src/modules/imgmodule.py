class Image:
    def __init__(self, datarow):
        self.image_uid = datarow['image_uid']
        self.file_name = datarow['file_name']
        self.full_path = datarow['full_path']
        self.ext = datarow['ext']
        self.status = datarow['status']

class Saucenao_Result:
    def __init__(self, datarow):
        self.result_uid = datarow['result_uid']
        self.image_uid = datarow['image_uid']
        self.site_flag = datarow['site_flag']
        self.site_id = datarow['site_id']
        self.similarity = datarow['similarity']
        self.status = datarow['status']
