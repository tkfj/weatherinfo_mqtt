"""
"""

import datetime
from jma_common import fetch_text, fetch_json, parse_dt_str

amedastable_url : str = 'https://www.jma.go.jp/bosai/amedas/const/amedastable.json'
amedas_latest_time_url : str = 'https://www.jma.go.jp/bosai/amedas/data/latest_time.txt'
amedas_url_format : str = 'https://www.jma.go.jp/bosai/amedas/data/point/{amedas_point_cd}/{y:04d}{m:02d}{d:02d}_{h3:02d}.json'

def get_amedas_latest_time() -> datetime.datetime:
    latest_txt : str = fetch_text(amedas_latest_time_url)
    latest_dt : datetime.datetime = parse_dt_str(latest_txt)
    return latest_dt

def get_amedas_point(amedas_point_cd: str) -> dict:
    pointjson : dict = fetch_json(amedastable_url)[amedas_point_cd]
    lat_t : tuple[int,float] = pointjson['lat']
    lon_t : tuple[int,float] = pointjson['lon']
    lat : float = lat_t[0] + lat_t[1] / 60 # 度が負の場合の分の扱いは確認が必要(国内に限る場合は考慮不要)
    lon : float = lon_t[0] + lon_t[1] / 60
    return {
        'nm' : pointjson['kjName'],
        'nm_kana' : pointjson['knName'],
        'nm_en' : pointjson['enName'],
        'lat' : lat,
        'lon' : lon,
        'alt' : pointjson['alt'],
        'type' : pointjson['type'],
        'elems' : pointjson['elems']
    }

def get_amedas_url(amedas_point_cd: str, amedas_latest_dt: datetime.datetime) -> str:
    return amedas_url_format.format(
        amedas_point_cd = amedas_point_cd,
        y = amedas_latest_dt.year,
        m = amedas_latest_dt.month,
        d = amedas_latest_dt.day,
        h3 = (amedas_latest_dt.hour // 3) * 3,
    )

def get_amedas_point_data_raw(amedas_point_cd: str, dt: datetime.datetime) -> dict:
    amedas_url : str = get_amedas_url(amedas_point_cd, dt)
    amedas_data_all : dict = fetch_json(amedas_url)
    return amedas_data_all

def get_amedas_point_data_latest(amedas_point_cd: str) -> dict:
    amedas_latest_dt : datetime.datetime = get_amedas_latest_time()
    amedas_data_all : dict = get_amedas_point_data_raw(amedas_point_cd, amedas_latest_dt)
    # 最新時刻
    data_k : str = amedas_latest_dt.strftime('%Y%m%d%H%M%S')
    amedas_data : dict = amedas_data_all[data_k]
    # 最新の毎時0分
    data_k0 : str = data_k[:-4]+'0000'
    amedas_data0 : dict = amedas_data_all[data_k0]
    # 最新データに、毎時0分のみ発表のデータをマージ
    amedas_data_j : dict = { _k : amedas_data[_k] if _k in amedas_data else amedas_data0[_k] for _k in amedas_data0 }
    return amedas_data_j

def amedas_data_flatten(amedas_data: dict) -> dict:
    dic = dict()
    for _k, _v in amedas_data.items():
        if (isinstance(_v, list) or isinstance(_v, tuple)) and len(_v) == 2 and (isinstance(_v[1],int) or _v[1] is None):
            # AQC付きのデータを測定値とAQCの別項目に分割
            dic[_k] = _v[0]
            dic[f'{_k}Aqc'] = _v[1]
        elif _k[-4:] == 'Time' and isinstance(_v, dict) and len(_v) == 2 and 'hour' in _v and isinstance(_v['hour'], int) and 'minute' in _v and isinstance(_v['minute'], int):
            # 発生時刻のデータをhh:mm形式の文字列に変換. UTCをJSTに変換.
            jh = (_v['hour'] + 9) % 24
            jm = _v['minute']
            dic[_k] = f'{jh:02d}:{jm:02d}'
        else:
            dic[_k] = _v
    return dic
    
if __name__ == '__main__':
    from pprint import pprint
    point_cd : str = '44172' # 東京-大島
    data_j : dict = amedas_data_flatten(get_amedas_point_data_latest(point_cd))
    pprint(data_j)
