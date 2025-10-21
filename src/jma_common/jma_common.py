"""
common utilities
"""

import datetime
import json
import requests

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

    def fetch(self, datatype:type, url:str, **kwargs)->str|bytes:
        """
        get data not using cache
        """
        resp = _fetch(url, **kwargs)
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

def _fetch(url:str, **kwargs)->requests.Response:
    """
    request to URL, internal use only
    """
    if _DEBUG_ADDRESS_:
        print(url)
    if 'timeout' in kwargs:
        timeout = kwargs['timeout']
        del kwargs['timeout']
    else:
        timeout = 3000
    resp = requests.get(url, timeout=timeout, **kwargs)
    if _DEBUG_ADDRESS_:
        print(f'{resp.status_code} {resp.reason}')
    return resp

def fetch_text(url:str, cache_key:str|None=None)->str:
    """
    fetch text data from URL
    """
    return cache.get(str, url, cache_key)

def fetch_json(url:str, cache_key:str|None=None)->any:
    """
    fetch json data from URL
    """
    json_raw = fetch_text(url,cache_key=cache_key)
    json_obj = json.loads(json_raw)
    return json_obj

def fetch_binary(url:str, cache_key:str|None=None)->any:
    """
    fetch binary data from URL
    """
    return cache.get(url, bytes, cache_key)

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

def get_area_cd_office_by_class10(area_cd:str, use_cache:bool=True)-> str:
    """
    get area_cd of office by class10 in `area` data
    """
    area_data = fetch_area(use_cache=use_cache)
    return area_data['class10s'][area_cd]['parent']
