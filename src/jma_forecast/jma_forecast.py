"""
番号 天気
"""

import copy
from pprint import pprint
import datetime
from jma_common import fetch_json, parse_dt_str, format_dt_str

forecast_url_format : str = 'https://www.jma.go.jp/bosai/forecast/data/forecast/{area_cd}.json'
weather_code_labels = {
    '100': '晴れ',
    '101': '晴れ時々くもり',
    '102': '晴れ一時雨',
    '103': '晴れ時々雨',
    '104': '晴れ一時雪',
    '105': '晴れ時々雪',
    '106': '晴れ一時雨か雪',
    '107': '晴れ時々雨か雪',
    '110': '晴れ後時々くもり',
    '111': '晴れ後くもり',
    '112': '晴れ後一時雨',
    '113': '晴れ後時々雨',
    '114': '晴れ後雨',
    '115': '晴れ後一時雪',
    '116': '晴れ後時々雪',
    '117': '晴れ後雪',
    '118': '晴れ後雨か雪',
    '160': '晴れ一時雪か雨',
    '170': '晴れ時々雪か雨',
    '181': '晴れ後雪か雨',
    '200': 'くもり',
    '201': 'くもり時々晴れ',
    '202': 'くもり一時雨',
    '203': 'くもり時々雨',
    '204': 'くもり一時雪',
    '205': 'くもり時々雪',
    '206': 'くもり一時雨か雪',
    '207': 'くもり時々雨か雪',
    '210': 'くもり後時々晴れ',
    '211': 'くもり後晴れ',
    '212': 'くもり後一時雨',
    '213': 'くもり後時々雨',
    '214': 'くもり後雨',
    '215': 'くもり後一時雪',
    '216': 'くもり後時々雪',
    '217': 'くもり後雪',
    '218': 'くもり後雨か雪',
    '260': 'くもり一時雪か雨',
    '270': 'くもり時々雪か雨',
    '281': 'くもり後雪か雨',
    '300': '雨',
    '301': '雨時々晴れ',
    '302': '雨時々止む',
    '303': '雨時々雪',
    '304': '雨か雪',
    '308': '雨で暴風を伴う',
    '309': '雨一時雪',
    '311': '雨後晴れ',
    '313': '雨後くもり',
    '314': '雨後時々雪',
    '315': '雨後雪',
    '316': '雨か雪後晴れ',
    '317': '雨か雪後くもり',
    '340': '雪か雨',
    '361': '雪か雨後晴れ',
    '371': '雪か雨後くもり',
    '400': '雪',
    '401': '雪時々晴れ',
    '402': '雪時々止む',
    '403': '雪時々雨',
    '406': '風雪強い',
    '407': '暴風雪',
    '409': '雪一時雨',
    '411': '雪後晴れ',
    '413': '雪後くもり',
    '414': '雪後雨',
}

def get_forecast_url(area_cd: str) -> str:
    return forecast_url_format.format(
        area_cd = area_cd,
    )

def get_forecast_data_raw(area_cd: str) -> dict:
    url : str = get_forecast_url(area_cd)
    data_raw : dict = fetch_json(url)
    # pprint(data_raw)
    return data_raw

def get_forecast_data_sub(area_cd: str, area_sub_cd: str) -> dict:
    def sel(parent:dict):
        _a = parent['areas'] 
        del parent['areas']
        parent['areas'] = _a[areaidx]

    data_raw : dict = get_forecast_data_raw(area_cd)
    for _i, _a in enumerate(data_raw[0]['timeSeries'][0]['areas']):
        if _a['area']['code']==area_sub_cd:
            areaidx:int = _i
            break
    else:
        raise ValueError(f'area sub code not found: {area_sub_cd}')
    data_sel = copy.deepcopy(data_raw)
    for _as in data_sel[0]['timeSeries']:
        sel(_as)
    for _as in data_sel[1]['timeSeries']:
        sel(_as)
    sel(data_sel[1]['precipAverage'])
    sel(data_sel[1]['tempAverage'])
    return data_sel

def get_forecast_data_pretty(area_cd: str, area_sub_cd: str) -> dict:
    data_sel : dict = get_forecast_data_sub(area_cd, area_sub_cd)
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
                pops = max(map(lambda x: int(x), _d["pops"]))
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
            weather_label = weather_code_labels[weather_code]
            if '雪' in weather_label and '雨' in weather_label:
                weather_label_hass = 'snowy-rainy'
            elif '雪' in weather_label:
                weather_label_hass = 'snowy'
            elif '雨' in weather_label:
                weather_label_hass = 'rainy'
            elif '晴れ' == weather_label:
                weather_label_hass = 'sunny'
            elif 'くもり' == weather_label:
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
    # TODO 130010  から、area.jsonみたいなのでparentをひっぱって、そのURLでデータをとって、そこから見つけ出せ？
    area_cd : str = '130000' # 東京-東京
    area_sub_cd : str = '130010' # 東京-東京
    data_j : dict = get_forecast_data_pretty(area_cd, area_sub_cd)
    pprint(data_j)
