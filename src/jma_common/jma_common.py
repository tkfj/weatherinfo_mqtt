import datetime
import json
import requests

_DEBUG_ADDRESS_ = True

def fetch_text(url:str)->str:
    if _DEBUG_ADDRESS_:
        print(url)
    resp = requests.get(url)
    if _DEBUG_ADDRESS_:
        print(f'{resp.status_code} {resp.reason}')
    text_raw = resp.text
    return text_raw

def fetch_json(url:str)->any:
    json_raw = fetch_text(url)
    json_obj = json.loads(json_raw)
    return json_obj

def parse_dt_str(dt_str:str)->datetime.datetime:
    return datetime.datetime.fromisoformat(dt_str)

def format_dt_str(dt:datetime.datetime)->str:
    return dt.isoformat()

area_url : str = 'https://www.jma.go.jp/bosai/common/const/area.json'
def get_area_cd_office_by_class10(area_cd)-> str:
    area_data = fetch_json(area_url)
    return area_data['class10s'][area_cd]['parent']

