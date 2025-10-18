"""
"""

from pprint import pprint
import datetime
from jma_common import fetch_text, fetch_json, parse_dt_str

vpfd_url_format : str = 'https://www.jma.go.jp/bosai/jmatile/data/wdist/VPFD/{area_cd}.json'

def get_vpfd_url(area_cd: str) -> str:
    return vpfd_url_format.format(
        area_cd = area_cd,
    )

def get_vpfd_data_raw(area_cd: str) -> dict:
    url : str = get_vpfd_url(area_cd)
    data_raw : dict = fetch_json(url)
    pprint(data_raw)
    return data_raw

def get_vpfd_data_pretty(area_cd: str) -> dict:
    data_raw : dict = get_vpfd_data_raw(area_cd)
    area_time_series = {
        _t['dateTime']: {
            'weather': data_raw['areaTimeSeries']['weather'][_i],
            'wind': data_raw['areaTimeSeries']['wind'][_i],
        } for _i,_t in enumerate(data_raw['areaTimeSeries']['timeDefines'])
    }
    pprint(area_time_series)
    point_time_series = {
        _t['dateTime']: {
            'maxTemperature': data_raw['pointTimeSeries']['maxTemperature'][_i],
            'minTemperature': data_raw['pointTimeSeries']['minTemperature'][_i],
            'temperature': data_raw['pointTimeSeries']['temperature'][_i],
        } for _i,_t in enumerate(data_raw['pointTimeSeries']['timeDefines'])
    }
    pprint(point_time_series)
    time_series = [
        {
            'datetime': _timestr,
            'weather': area_time_series[_timestr]['weather'],
            'wind': area_time_series[_timestr]['wind'],
            'maxTemperature': point_time_series[_timestr]['maxTemperature'],
            'minTemperature': point_time_series[_timestr]['minTemperature'],
            'temperature': point_time_series[_timestr]['temperature'],
        } for _timestr in sorted(area_time_series.keys())
    ]
    pprint(time_series)
    return [
        {
            'datetime': _x['datetime'],
            'weather': _x['weather'],
            'wind_speed': _x['wind']['speed'],
            'wind_direction': _x['wind']['direction'],
            'gust_speed_low': int(_x['wind']['range'].split(' ')[0]),
            'gust_speed_high': int(_x['wind']['range'].split(' ')[1]),
            'maxTemperature': _x['maxTemperature'] if _x['maxTemperature'] else None,
            'minTemperature': _x['minTemperature'] if _x['minTemperature'] else None,
            'temperature': _x['temperature'],
        } for _x in time_series
    ]
    
if __name__ == '__main__':
    area_cd : str = '130010' # 東京-東京
    data_j : dict = get_vpfd_data_pretty(area_cd)
    pprint(data_j)
