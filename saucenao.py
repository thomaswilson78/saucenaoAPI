import os
import sys
import io
import json
import requests
import time
from PIL import Image
from collections import OrderedDict
from enum import Enum, IntFlag, auto


class API(object):
    def __init__(self, dbmask:int, minsim:int = 90, output_type:int = 2):
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


    class Output_Type(Enum):
        html = 0
        xml = 1 # NOT IMPLEMENTED!!!
        json = 2
        

    class DBMask(IntFlag):
        """Flags that correspond to the appropriate website. To be used for including/excluding in search."""
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


    def __get_image_data(fname):
        """Extracts the image's bytes and adds it as a parameter to be used in the request."""
        image = Image.open(fname)
        image = image.convert('RGB')
        image.thumbnail(API.__THUMBSIZE, resample=Image.ANTIALIAS)
        imageData = io.BytesIO()
        image.save(imageData,format='PNG')
        file = {'file': ("image.png", imageData.getvalue())}
        imageData.close()
        image.close()
        
        return file
    
    
    def __set_params(self, params:dict[str:any]) -> dict[str:any]:
        """Sets required parameters that were initialized in constructor."""
        params["minsim"] = self.minsim
        params["output_type"] = self.output_type
        params["dbmask"] = self.dbmask
        params["api_key"] = self.__API_KEY
        return params


    def send_request(self, fname: str, params: dict[str:any] = {}):
        """Sends request to Saucenao's API and returns response.

        fname: The full file name of the file that will be extracted and sent.
        params: Additional parameters to include in search (any parameters set in constructor will use those values).
        """
        results = []
        file = API.__get_image_data(fname)
        params = self.__set_params(params)

        while True:
            r = requests.post("http://saucenao.com/search.php", params=params, files=file)
            if r.status_code != 200:
                if r.status_code == 403:
                    print("Incorrect or Invalid API Key!")
                    sys.exit(1)
                elif r.status_code == 429:
                    print("Reached search limit, unable to process more request at this time.")
                    sys.exit()
                else:
                    #generally non 200 statuses are due to either overloaded servers or the user is out of searches
                    print("Status Code: "+str(r.status_code))
                    time.sleep(10)
            else:
                results = json.JSONDecoder(object_pairs_hook=OrderedDict).decode(r.text)
                if int(results["header"]["user_id"])>0:
                    #api responded
                    print("Remaining Searches 30s|24h: "+str(results["header"]["short_remaining"])+"|"+str(results["header"]["long_remaining"]))
                    if int(results["header"]["status"])==0:
                        #search succeeded for all indexes, results usable
                        break
                    else:
                        if int(results["header"]["status"])>0:
                            #One or more indexes are having an issue.
                            #This search is considered partially successful, even if all indexes failed, so is still counted against your limit.
                            #The error may be transient, but because we don"t want to waste searches, allow time for recovery.
                            print("API Error. Retrying in 600 seconds...")
                            time.sleep(600)
                            continue
                        else:
                            #Problem with search as submitted, bad image, or impossible request.
                            #Issue is unclear, so don"t flood requests.
                            print("Bad image or other request error. Skipping.")
                            results = []
                            time.sleep(10)
                            break
                else:
                    #General issue, api did not respond. Normal site took over for this error state.
                    #Issue is unclear, so don"t flood requests.
                    print("Bad image or API failure. Skipping.")
                    results = []
                    time.sleep(10)
                    break

        return results
