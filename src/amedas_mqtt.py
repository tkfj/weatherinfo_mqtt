import datetime
import json
import os

import dotenv
import paho.mqtt.client as mqtt
from paho.mqtt.enums import CallbackAPIVersion

from pprint import pprint

from jma_common import parse_dt_str, get_area_cd_office_by_class10,get_area_cd_class10_by_class15,get_area_cd_class15_by_class20,get_sunny_or_clear_night
from jma_amedas import get_amedas_latest_time, get_amedas_point_data_latest, amedas_data_flatten
from jma_vpfd import get_vpfd_data_pretty
from jma_forecast import get_forecast_data_pretty
from jma_nowcast import get_nowc_forecast
from jma_bunpu import get_bunpu_area_coordinates,get_bunpu_weather

dotenv.load_dotenv()

mqtt_broker = os.environ.get('MQTT_BROKER')
mqtt_port = int(os.environ.get('MQTT_PORT','1883'))
mqtt_username = os.environ.get('MQTT_USERNAME')
mqtt_password = os.environ.get('MQTT_PASSWORD')
mqtt_topic_amedas_stat = os.environ.get('MQTT_TOPIC_AMEDAS_STAT')
mqtt_topic_amedas_attr = os.environ.get('MQTT_TOPIC_AMEDAS_ATTR')
mqtt_topic_amedas_avty = os.environ.get('MQTT_TOPIC_AMEDAS_AVTY')

map_lat=float(os.environ['NOWCAST_RAIN_LAT'])
map_lon=float(os.environ['NOWCAST_RAIN_LNG'])

amedas_point_cd = os.environ.get('JMA_AMEDAS_POINT_CD')

area_cd_class20 = os.environ.get('JMA_AREA_CD_CLASS20')
area_cd_class15 = get_area_cd_class15_by_class20(area_cd_class20)
area_cd_class10 = get_area_cd_class10_by_class15(area_cd_class15)
area_cd_office = get_area_cd_office_by_class10(area_cd_class10)

amedas_data = amedas_data_flatten(get_amedas_point_data_latest(amedas_point_cd))

bunpu_tile_cd, bunpu_tile_pxl_x, bunpu_tile_pxl_y = get_bunpu_area_coordinates(map_lat,map_lon)

amedas_latest_time = get_amedas_latest_time()
bunpu_weather = get_bunpu_weather(bunpu_tile_cd, bunpu_tile_pxl_x, bunpu_tile_pxl_y, amedas_latest_time)

def convert_vpdf_weather(w: str, dtstr: str|None = None)-> str:
    match w:
        case '晴れ':
            return get_sunny_or_clear_night(datetime.datetime.fromisoformat(dtstr))
        case 'くもり':
            return 'cloudy'
        case '雨':
            return 'rainy'
        case '雨または雪':
            return 'snowy-rainy'
        case '雪':
            return 'snowy'
        
def convert_vpdf_direction(d: str)-> int:
    match d:
        case '北':
            return 0
        case '北東':
            return 45
        case '東':
            return 90
        case '南東':
            return 135
        case '南':
            return 180
        case '南西':
            return 225
        case '西':
            return 270
        case '北西':
            return 315

# ナウキャスト降水情報
nowc_forecast = get_nowc_forecast(map_lat,map_lon)
# 現在及び5分後に降水なしならクリア、それ以外は雨
nowc_weather = 'clear' if nowc_forecast[0][2]==0 and nowc_forecast[1][2]==0 else 'rainy'
pprint(nowc_forecast)

def get_overall_weather(amedas_data:any, nowc_weather:str, bunpu_weather:str, dt:datetime):
    """
    アメダス、ナウキャスト降水情報、推計気象分布から判断した現在の天気
    """
    if nowc_weather == 'rainy':
        # ナウキャストが雨の場合、降水は確定で、気温に応じて雪の判定
        if amedas_data['temp']>2:
            return 'rainy'
        elif amedas_data['temp']<0:
            return 'snowy'
        else:
            return 'snowy-rainy'
    elif bunpu_weather in ['rainy','snowy-rainy','snowy']:
        # (ナウキャストがクリアで)推計気象分布が降水の場合、
        # アメダスで日照があればクリア、なければ曇り
        # （たぶん夜間は曇り扱いになってしまうが推計気象分布が降水なら曇りだろう）
        if amedas_data['sun10m']>0:
            return get_sunny_or_clear_night(dt)
        else:
            return 'cloudy'
    elif amedas_data['sun10m']>0:
        # (ナウキャストがクリアで推計気象分布が降水なしで)アメダスで日照があればクリア
        return get_sunny_or_clear_night(dt)
    # (ナウキャストがクリアで推計気象分布が降水なしで)アメダスで日照がなければ推計気象分布に従う
    return bunpu_weather

overall_weather = get_overall_weather(amedas_data, nowc_weather, bunpu_weather, amedas_latest_time)

vpfd=get_vpfd_data_pretty(area_cd_class10)
fcst=get_forecast_data_pretty(area_cd_class10)
fcst_h=[
    {
        'datetime': _x['datetime'],
        'condition':convert_vpdf_weather(_x['weather'], _x['datetime']),
        'temperature':_x['temperature'],
        'templow':_x['minTemperature'],
        'wind_speed':_x['wind_speed'],
        'wind_gust_speed':_x['gust_speed_high'],
        'wind_bearing':convert_vpdf_direction(_x['wind_direction']),
    } for _x in vpfd
]
fcst_d=[
    {
        'datetime': _t,
        'condition':_x['weather_hass'],
        'temperature':_x['temp_max'],
        'templow':_x['temp_min'],
    } for _t,_x in fcst.items() if parse_dt_str(_t) > datetime.datetime.now().astimezone(datetime.timezone.utc)
]
# アメダスの風向を角度に変換。16は風が弱くて特定できていない状態
amedas_data['windDirection'] = float(amedas_data['windDirection'] * 22.5) if amedas_data['windDirection']<16 else None
amedas_data['gustDirection'] = float(amedas_data['gustDirection'] * 22.5) if amedas_data['gustDirection']<16 else None
amedas_data['nowc_weather'] = nowc_weather
amedas_data['bunpu_weather'] = bunpu_weather
amedas_data['overall_weather'] = overall_weather
amedas_data['forecast_hourly'] = fcst_h
amedas_data['forecast_daily'] = fcst_d
for _i, _x in enumerate(nowc_forecast):
    amedas_data[f'nowc_rain_{_i*5:02d}']=_x[2]

pprint(amedas_data)

mqtt_cli = mqtt.Client(CallbackAPIVersion.VERSION2)
if (mqtt_username) or (mqtt_password):
    mqtt_cli.username_pw_set(mqtt_username, mqtt_password) 
mqtt_cli.connect(mqtt_broker, mqtt_port, 60)
mqtt_cli.loop_start()

pub1 = mqtt_cli.publish(mqtt_topic_amedas_stat, overall_weather, qos=1, retain=True)
pub2 = mqtt_cli.publish(mqtt_topic_amedas_attr, json.dumps(amedas_data), qos=1, retain=True)
pub3 = mqtt_cli.publish(mqtt_topic_amedas_avty, 'online', qos=1, retain=True)

#送信完了までプログラムを落とさないように待つ
pub1.wait_for_publish()
pub2.wait_for_publish()
pub3.wait_for_publish()

mqtt_cli.disconnect()
mqtt_cli.loop_stop()
