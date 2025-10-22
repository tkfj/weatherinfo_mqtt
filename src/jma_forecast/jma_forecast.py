"""
天気予報
https://www.jma.go.jp/bosai/forecast/
"""

import copy
from pprint import pprint
import datetime
import json
import os
from jma_common import fetch_json, parse_dt_str, format_dt_str, get_area_cd_office_by_class10

forecast_url_format : str = 'https://www.jma.go.jp/bosai/forecast/data/forecast/{area_cd_office}.json'

def _load_weather_codes():
    module_path = os.path.abspath(__file__)
    module_dir = os.path.dirname(module_path)
    json_path = os.path.join(module_dir, 'telops.json')
    print(module_path, module_dir, json_path)
    with open(json_path, 'rt', encoding='utf-8') as jsonf:
        json_raw = json.load(jsonf)
    return {
        _k:{
            'icon_day': _v[0],
            'icon_night': _v[1],
            'primary_weather': _v[2],
            'label_ja': _v[3],
            'label_en': _v[4],
        } for _k, _v in json_raw.items()
    }

_weather_codes = _load_weather_codes()

def get_forecast_url(area_cd_office: str) -> str:
    return forecast_url_format.format(
        area_cd_office = area_cd_office,
    )

def get_forecast_data_raw(area_cd_office: str) -> dict:
    url : str = get_forecast_url(area_cd_office)
    data_raw : dict = fetch_json(url)
    # pprint(data_raw)
    return data_raw

def get_forecast_data_sub(area_cd_class10: str) -> dict:
    area_code_office = get_area_cd_office_by_class10(area_cd_class10)
    def sel(parent:dict):
        _a = parent['areas']
        del parent['areas']
        parent['areas'] = _a[areaidx]

    data_raw : dict = get_forecast_data_raw(area_code_office)
    for _i, _a in enumerate(data_raw[0]['timeSeries'][0]['areas']):
        if _a['area']['code']==area_cd_class10:
            areaidx:int = _i
            break
    else:
        raise ValueError(f'area sub code not found: {area_cd_class10}')
    data_sel = copy.deepcopy(data_raw)
    for _as in data_sel[0]['timeSeries']:
        sel(_as)
    #TODO 3日天気予報より7日天気予報のほうが予報地点が少ない。マッピング用のjsonがある？。week_area05.json
    #むしろweek_area.jsonがすべて持ってるのでは。
    for _as in data_sel[1]['timeSeries']:
        sel(_as)
    sel(data_sel[1]['precipAverage'])
    sel(data_sel[1]['tempAverage'])
    return data_sel

def get_forecast_data_pretty(area_cd_class10: str) -> dict:
    data_sel : dict = get_forecast_data_sub(area_cd_class10)
    # pprint(data_sel)
    ts3:dict = dict()
    ts7:dict = dict()
    for _ts in data_sel[0]['timeSeries']:
        for _n in ['waves','weatherCodes','weathers','winds','pops','temps']:
            if _n in _ts['areas']:
                ts3[_n] = { _k:_v for _k,_v in zip(_ts['timeDefines'],_ts['areas'][_n])}
    for _ts in data_sel[1]['timeSeries']:
        for _n in ['weatherCodes','pops','reliabilities','tempsMax','tempsMaxLower','tempsMaxUpper','tempsMin','tempsMinLower','tempsMinUpper']:
            if _n in _ts['areas']:
                ts7[_n] = { _k:_v for _k,_v in zip(_ts['timeDefines'],_ts['areas'][_n])}
    ts3pops = dict()
    for _t,_v in ts3['pops'].items():
        _ts = format_dt_str(parse_dt_str(_t).replace(hour=0,minute=0,second=0,microsecond=0))
        if _ts in ts3pops:
            ts3pops[_ts].append(_v)
        else:
            ts3pops[_ts]=[_v]
    ts3['pops'] = ts3pops
    ts3['tempsMax']=dict()
    ts3['tempsMin']=dict()
    for _t,_v in ts3['temps'].items():
        _tsdt = parse_dt_str(_t)
        _ts = format_dt_str(_tsdt.replace(hour=0,minute=0,second=0,microsecond=0))
        if _tsdt.hour == 0:
            ts3['tempsMin'][_ts]=_v
        elif _tsdt.hour == 9:
            ts3['tempsMax'][_ts]=_v
    del ts3['temps']
    ts3['weatherCodes'] = {format_dt_str(parse_dt_str(_t).replace(hour=0,minute=0,second=0,microsecond=0)): _v for _t,_v in ts3['weatherCodes'].items()}

    ret = dict()
    for _k, _ts in ts7.items():
        if _k not in ['weatherCodes', 'pops','tempsMax', 'tempsMin']:
            continue
        for _t, _v in _ts.items():
            if _t not in ret:
                ret[_t]=dict()
            ret[_t][_k]=_v
    for _k, _ts in ts3.items():
        if _k not in ['weatherCodes', 'pops','tempsMax', 'tempsMin']:
            continue
        for _t, _v in _ts.items():
            if _t not in ret:
                ret[_t]=dict()
            ret[_t][_k]=_v

    def norm(_d: dict):
        if "pops" in _d:
            if isinstance(_d["pops"], list):
                pops = max(map(int, _d["pops"]))
            elif isinstance(_d["pops"],str):
                pops = int(_d["pops"])
            else:
                pops = None
        else:
            pops = None
        if "tempsMax" in _d:
            temps_max = int(_d["tempsMax"])
        else:
            temps_max = None
        if "tempsMin" in _d:
            temps_min = int(_d["tempsMin"])
        else:
            temps_min = None
        if "weatherCodes" in _d:
            weather_code = _d["weatherCodes"]
            weather_label = _weather_codes[weather_code]['label_ja']
            if '雪' in weather_label and '雨' in weather_label:
                weather_label_hass = 'snowy-rainy'
            elif '雪' in weather_label:
                weather_label_hass = 'snowy'
            elif '雨' in weather_label:
                weather_label_hass = 'rainy'
            elif '晴' == weather_label:
                weather_label_hass = 'sunny'
            elif '曇' == weather_label:
                weather_label_hass = 'cloudy'
            else:
                weather_label_hass = 'partlycloudy'
        else:
            weather_code = None
            weather_label = None
            weather_label_hass = None
        return {
            'pop': pops,
            'temp_max': temps_max,
            'temp_min': temps_min,
            'weather_code': weather_code,
            'weather': weather_label,
            'weather_hass': weather_label_hass,
        }
    return { _t: norm(_v) for _t,_v in ret.items() }

if __name__ == '__main__':
    area_cd : str = '130010' # 東京-東京
    data_j : dict = get_forecast_data_pretty(area_cd)
    pprint(data_j)
