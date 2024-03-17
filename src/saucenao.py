import os
import io
import json
import requests
from PIL import Image, ImageFile
from collections import OrderedDict
from enum import Enum, IntFlag, auto
import src.saucenaoconfig as saucenaoconfig


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


    def __init__(self, dbmask:int, minsim:int = 90, output_type:Output_Type = Output_Type.json):
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
        image = Image.open(fname)
        image = image.convert('RGB')
        dimensions = image.size
        image.thumbnail(API.__THUMBSIZE, resample=Image.ANTIALIAS)
        imageData = io.BytesIO()
        image.save(imageData,format='PNG')
        file = {'file': ("image.png", imageData.getvalue())}
        imageData.close()
        image.close()
        
        return (file, dimensions)
    
    
    def __set_params(self, params:dict[str:any]) -> dict[str:any]:
        """Sets required parameters that were initialized in constructor."""
        params["minsim"] = str(self.minsim) + "!"
        params["output_type"] = self.output_type.value
        params["dbmask"] = self.dbmask
        params["api_key"] = self.__API_KEY
        return params
    
    
    def __test_response(self): 
        """For debugging purposes, send a simulated response to prevent usage of daily searches."""

        # Provides 3 results: above 90, between 90-60, and below 60.
        return """{
                  "header": {
                    "user_id": "117582",
                    "account_type": "1",
                    "short_limit": "4",
                    "long_limit": "100",
                    "long_remaining": 90,
                    "short_remaining": 3,
                    "status": 0,
                    "results_requested": "8",
                    "index": {
                      "9": {
                        "status": 0,
                        "parent_id": 9,
                        "id": 9,
                        "results": 8
                      }
                    },
                    "search_depth": "128",
                    "minimum_similarity": 0,
                    "query_image_display": "\\/userdata\\/4u6TvvoH6.png.png",
                    "query_image": "4u6TvvoH6.png",
                    "results_returned": 8
                  },
                  "results": [
                    {
                      "header": {
                        "similarity": "96.22",
                        "thumbnail": "https:\\/\\/img3.saucenao.com\\/booru\\/f\\/6\\/f603559b53625c48d47e5cba07cb380a_0.jpg?auth=AtyVEePg7VbVaI_Rx0uX9A\\u0026exp=1710874800",
                        "index_id": 9,
                        "index_name": "Index #9: Danbooru - f603559b53625c48d47e5cba07cb380a_0.jpg",
                        "dupes": 0,
                        "hidden": 0
                      },
                      "data": {
                        "ext_urls": [
                          "https:\\/\\/danbooru.donmai.us\\/post\\/show\\/4701825"
                        ],
                        "danbooru_id": 2582414,
                        "creator": "kimblee",
                        "material": "granblue fantasy",
                        "characters": "andira (granblue fantasy), andira (summer) (granblue fantasy)",
                        "source": "https:\\/\\/i.pximg.net\\/img-original\\/img\\/2021\\/08\\/14\\/00\\/00\\/13\\/91953701"
                      }
                    },
                    {
                      "header": {
                        "similarity": "78.84",
                        "thumbnail": "https:\\/\\/img3.saucenao.com\\/booru\\/b\\/5\\/b584e1c1f46338cd06be1c238c80955e_0.jpg?auth=ItKA4sEO2vFBWCQkZKSNIw\\u0026exp=1710874800",
                        "index_id": 9,
                        "index_name": "Index #9: Danbooru - b584e1c1f46338cd06be1c238c80955e_0.jpg",
                        "dupes": 0,
                        "hidden": 0
                      },
                      "data": {
                        "ext_urls": [
                          "https:\\/\\/danbooru.donmai.us\\/post\\/show\\/2710323"
                        ],
                        "danbooru_id": 2710323,
                        "creator": "kanachirou",
                        "material": "kantai collection",
                        "characters": "prinz eugen (kancolle)",
                        "source": "https:\\/\\/i.pximg.net\\/img-original\\/img\\/2017\\/05\\/02\\/11\\/40\\/34\\/62691361"
                      }
                    },
                    {
                      "header": {
                        "similarity": "52.72",
                        "thumbnail": "https:\\/\\/img3.saucenao.com\\/booru\\/8\\/8\\/88928dbe56a45a736233dba64f555707_0.jpg?auth=31A_R1-QK5r88ve2IyEE8w\\u0026exp=1710874800",
                        "index_id": 9,
                        "index_name": "Index #9: Danbooru - 88928dbe56a45a736233dba64f555707_0.jpg",
                        "dupes": 0,
                        "hidden": 0
                      },
                      "data": {
                        "ext_urls": [
                          "https:\\/\\/danbooru.donmai.us\\/post\\/show\\/6179125"
                        ],
                        "danbooru_id": 6179125,
                        "creator": "nashi chai1346",
                        "material": "genshin impact, indie virtual youtuber",
                        "characters": "nilou (genshin impact), nini yuuna",
                        "source": "https:\\/\\/twitter.com\\/nashi_tw\\/status\\/1581261904169021440"
                      }
                    }
                  ]
                }"""


    def send_request(self, file: str, params: dict[str:any] = {}) -> dict[str:any]:
        """Sends request to Saucenao's API and returns response.

        file: Image file that will be extracted and sent.
        params: Additional parameters to include in search.
        """
        response = {}
        file, dimensions = API.__get_image_data(file)
        response["image"] = {"dimensions": dimensions}
        params = self.__set_params(params)

        if saucenaoconfig.IS_DEBUG:
            response["response"] = json.JSONDecoder(object_pairs_hook=OrderedDict).decode(self.__test_response())
        else:
            r = requests.post("http://saucenao.com/search.php", params=params, files=file)

            match r.status_code:
                case 403:
                    raise Exception("Incorrect or Invalid API Key!")
                case 429:
                    raise Exception("Out of daily searches. Try again later.")
                case 200:
                    response["response"] = json.JSONDecoder(object_pairs_hook=OrderedDict).decode(r.text)
                # Generally non-200 statuses are due to some other issue like overloaded servers
                case _:
                    raise Exception(f"Status Code: {r.status_code}\nMessage: {r.reason}")

        return response


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
