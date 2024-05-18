import os
import io
import json
import requests
from PIL import Image, ImageFile
from enum import Enum, IntFlag, auto


class API(object):
    """Library that interacts with Saucenao's REST API tools."""
    class Output_Type(Enum):
        """Response output type expected from Saucenao.
        
        NOTE: As of this time XML is not implemented and should not be used."""
        html = 0
        xml = 1 # NOT IMPLEMENTED!!!
        json = 2
        

    class DBMask(IntFlag):
        """Flags that correspond to the appropriate website. To be used for including/excluding results in search."""
        index_hmags = auto()
        index_reserved = auto()
        index_hcg = auto()
        index_ddbobjects = auto()
        index_ddbsamples = auto()
        index_pixiv = auto()
        index_pixivhistorical = auto()
        index_reserved2 = auto()
        index_seigaillust = auto()
        index_danbooru = auto()
        index_drawr = auto()
        index_nijie = auto()
        index_yandere = auto()
        index_animeop = auto()
        index_reserved3 = auto()
        index_shutterstock = auto()
        index_fakku = auto()
        index_hmisc = auto()
        index_2dmarket = auto()
        index_medibang = auto()
        index_anime = auto()
        index_hanime = auto()
        index_movies = auto()
        index_shows = auto()
        index_gelbooru = auto()
        index_konachan = auto()
        index_sankaku = auto()
        index_animepictures = auto()
        index_e621 = auto()
        index_idolcomplex = auto()
        index_bcyillust = auto()
        index_bcycosplay = auto()
        index_portalgraphics = auto()
        index_da = auto()
        index_pawoo = auto()
        index_madokami = auto()
        index_mangadex = auto()


    def __init__(self, dbmask:int, minsim:int, output_type:Output_Type = Output_Type.json):
        self.dbmask = dbmask
        self.minsim = minsim
        self.output_type = output_type


    # Needs to be set as an environmental variable, set this in your .bashrc, .zshrc, or whatever shell you use on Linux,
    # alternatively for Windows/MacOSX look up how to add environmental variables
    __API_KEY = os.getenv("SAUCENAO_APIKEY")
    __THUMBSIZE = (250,250)
    __ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".gif", ".bmp"}
    # Why the hell does python not allow you to return an iterable from a property? 
    # This is the one good occasion for a property and I can't even use it.
    def get_allowed_extensions():
        return API.__ALLOWED_EXTENSIONS


    def __get_image_data(fname):
        """Extracts the image's bytes and adds it as a parameter to be used in the request."""
        ImageFile.LOAD_TRUNCATED_IMAGES = True
        with Image.open(fname) as image:
            image = image.convert('RGB')
            image.thumbnail(API.__THUMBSIZE, resample=Image.ANTIALIAS)
            with io.BytesIO() as imageData:
                image.save(imageData,format='PNG')
                file = {'file': ("image.png", imageData.getvalue())}
        
        return file
    
    
    def __set_params(self, params:dict[str:any]) -> dict[str:any]:
        """Sets required parameters that were initialized in constructor."""
        params["minsim"] = str(self.minsim) + "!"
        params["output_type"] = self.output_type.value
        params["dbmask"] = self.dbmask
        params["api_key"] = self.__API_KEY
        return params
    
    
    def test_response(self): 
        """For debugging purposes, returns a simulated JSON expected from Saucenao."""
        # Since the search limit is so tight this can be used in place as well as giving
        # multiple scenarios to work with.

        # Provides 3 different results: above 92, between 92-65, and below 65.
        return json.load(open("saucenao_sample.json"))


    def send_request(self, file: str, params: dict[str:any] = {}) -> dict[str:any]:
        """Sends image to Saucenao's API and returns any matches found in response.

        file: Image file that will be extracted and sent.
        params: Additional parameters to include in search.
        """
        
        file = API.__get_image_data(file)
        params = self.__set_params(params)

        return requests.post("http://saucenao.com/search.php", params=params, files=file)


class Result:
    class __Header:
        def __init__(self, resultsHeader):
            self.similarity:float = float(resultsHeader["similarity"])
            self.thumbnail:str = resultsHeader["thumbnail"]
            self.index_id:int = int(resultsHeader["index_id"])
            self.index_name:str = resultsHeader["index_name"]
            self.dupes:int = int(resultsHeader["dupes"])
            self.hidden:bool = bool(resultsHeader["hidden"])
    class __Data:
        def __init__(self, db_bitmask, resultsData):
            if db_bitmask & API.DBMask.index_danbooru:
                self.dan_id:int = int(resultsData["danbooru_id"])
            #Placeholder for both an example and if I decide to expand functionality
            #if db_bitmask & API.DBMask.index_gelbooru:
            #    self.gel_id:int = int(resultsData["gelbooru_id"])
        
    def __init__(self, db_bitmask, result) -> None:
        self.header = self.__Header(result["header"])
        self.data = self.__Data(db_bitmask, result["data"])
