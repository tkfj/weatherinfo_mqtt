"""
common utilities
"""

import datetime
from io import BytesIO
import json
import requests
from PIL import Image

_DEBUG_ADDRESS_ = True

area_url : str = 'https://www.jma.go.jp/bosai/common/const/area.json'

class _cache:
    """
    cache class, internal use only
    """
    def __init__(self):
        self.caches = dict()

    def get(self, datatype:type, url:str, cache_key:str|None = None, **kwargs)->str|bytes:
        """
        get data, using cache or not
        """
        if cache_key:
            return self.get_cache_or_fetch(datatype,url,cache_key,**kwargs)
        return self.fetch(datatype,url,**kwargs)

    def get_cache_or_fetch(self, datatype:type, url:str, cache_key:str, **kwargs)->str|bytes:
        """
        get data using cache, or fetch if missing
        """
        cached = self.caches.get(cache_key, None)
        if cached:
            return cached
        raw = self.fetch(datatype, url, **kwargs)
        self.set_cache(cache_key, raw)
        return raw

    def fetch(self, datatype:type, url:str, raise_error:bool=True, timeout:int=3000,**kwargs)->str|bytes:
        """
        get data from URL, not use cache
        """
        if _DEBUG_ADDRESS_:
            print(url)
        resp = requests.get(url, timeout=timeout, **kwargs)
        if _DEBUG_ADDRESS_:
            print(f'{resp.status_code} {resp.reason}')
        if raise_error:
            resp.raise_for_status()
        if datatype == str:
            raw = resp.text
        elif datatype == bytes:
            raw = resp.content
        else:
            raise ValueError(f'invalid datatype: {datatype}')
        return raw

    def del_cache(self, cache_key:str):
        """
        delete data from cache
        """
        if cache_key in self.caches:
            del self.caches[cache_key]

    def set_cache(self, cache_key:str, data:str|bytes):
        """
        add cache data
        """
        self.caches[cache_key] = data

cache = _cache()

def fetch_text(url:str, cache_key:str|None=None, **kwargs)->str:
    """
    fetch text data from URL
    """
    return cache.get(str, url, cache_key, **kwargs)

def fetch_json(url:str, cache_key:str|None=None, **kwargs)->any:
    """
    fetch json data from URL
    """
    json_raw = fetch_text(url,cache_key=cache_key, **kwargs)
    json_obj = json.loads(json_raw)
    return json_obj

def fetch_binary(url:str, cache_key:str|None=None, **kwargs)->any:
    """
    fetch binary data from URL
    """
    return cache.get(bytes, url, cache_key, **kwargs)

def fetch_image(url:str, cache_key:str|None=None, **kwargs)->any:
    """
    fetch image from URL
    """
    binary = fetch_binary(url, cache_key, **kwargs)
    return  Image.open(BytesIO(binary))

def parse_dt_str(dt_str:str)->datetime.datetime:
    """
    parse str to iso time
    """
    return datetime.datetime.fromisoformat(dt_str)

def format_dt_str(dt:datetime.datetime)->str:
    """
    format iso time to str
    """
    return dt.isoformat()

def fetch_area(use_cache:bool=True):
    """
    fetch `area` data
    """
    return fetch_json(area_url, cache_key='area' if use_cache else None)

def get_area_cd_center_by_office(office_cd:str, use_cache:bool=True)-> str:
    """
    get area_cd of center by office in `area` data
    """
    area_data = fetch_area(use_cache=use_cache)
    return area_data['offices'][office_cd]['parent']

def get_area_cd_office_by_class10(class10_cd:str, use_cache:bool=True)-> str:
    """
    get area_cd of office by class10 in `area` data
    """
    area_data = fetch_area(use_cache=use_cache)
    return area_data['class10s'][class10_cd]['parent']

def get_area_cd_class10_by_class15(class15_cd:str, use_cache:bool=True)-> str:
    """
    get area_cd of class10 by class15 in `area` data
    """
    area_data = fetch_area(use_cache=use_cache)
    return area_data['class15s'][class15_cd]['parent']

def get_area_cd_class15_by_class20(class20_cd:str, use_cache:bool=True)-> str:
    """
    get area_cd of class15 by class20 in `area` data
    """
    area_data = fetch_area(use_cache=use_cache)
    return area_data['class20s'][class20_cd]['parent']
