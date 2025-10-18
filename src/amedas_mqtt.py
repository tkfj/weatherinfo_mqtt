import datetime
import json
import os

import dotenv
import paho.mqtt.client as mqtt
from paho.mqtt.enums import CallbackAPIVersion

from jma_common import parse_dt_str
from jma_amedas import get_amedas_latest_time, get_amedas_point_data_latest, amedas_data_flatten
from jma_vpfd import get_vpfd_data_pretty
from jma_forecast import get_forecast_data_pretty

dotenv.load_dotenv()

mqtt_broker = os.environ.get('MQTT_BROKER')
mqtt_port = int(os.environ.get('MQTT_PORT','1883'))
mqtt_username = os.environ.get('MQTT_USERNAME')
mqtt_password = os.environ.get('MQTT_PASSWORD')
mqtt_topic_amedas_stat = os.environ.get('MQTT_TOPIC_AMEDAS_STAT')
mqtt_topic_amedas_attr = os.environ.get('MQTT_TOPIC_AMEDAS_ATTR')
mqtt_topic_amedas_avty = os.environ.get('MQTT_TOPIC_AMEDAS_AVTY')

amedas_point_cd = os.environ.get('JMA_AMEDAS_POINT_CD')

amedas_data = amedas_data_flatten(get_amedas_point_data_latest(amedas_point_cd))

mqtt_cli = mqtt.Client(CallbackAPIVersion.VERSION2)
if (mqtt_username) or (mqtt_password):
    mqtt_cli.username_pw_set(mqtt_username, mqtt_password) 
mqtt_cli.connect(mqtt_broker, mqtt_port, 60)
mqtt_cli.loop_start()

from PIL import Image
from io import BytesIO
import requests

def load_image_url(url):
    print(url)
    resp_img = requests.get(url)
    print(f'{resp_img.status_code} {resp_img.reason}')
    if resp_img.status_code == 404:
        return None
    resp_img.raise_for_status()
    return Image.open(BytesIO(resp_img.content))



bunpu_tile_cd='3016'
bunpu_tile_pxl_x=425
bunpu_tile_pxl_y=206

amedas_latest_time = get_amedas_latest_time()
while True:
    amedas_latest_time_s = amedas_latest_time.strftime('%Y%m%d%H')+'00'
    img1 = load_image_url(f'https://www.data.jma.go.jp/bunpu/img/wthr/{bunpu_tile_cd}/wthr_{bunpu_tile_cd}_{amedas_latest_time_s}.png')
    if img1 is not None: 
        break
    amedas_latest_time = amedas_latest_time - datetime.timedelta(hours=1)
pxl_color=img1.getpixel((bunpu_tile_pxl_x,bunpu_tile_pxl_y))
match pxl_color:
    case (0xff, 0xaa, 0x00, 0xff):
        weather = 'sunny' if 6<=amedas_latest_time.hour<18 else 'clear-night'
    case (0xaa, 0xaa, 0xaa, 0xff):
        weather = 'cloudy'
    case (0x00, 0x41, 0xff, 0xff):
        weather = 'rainy'
    case (0xf2, 0xf2, 0xff, 0xff):
        weather = 'snowy'
    case (0xa0, 0xd2, 0xff, 0xff):
        weather = 'snowy-rainy'
    case _:
        weather = 'exceptional'


def convert_vpdf_weather(w: str, dtstr: str|None = None)-> str:
    match w:
        case '晴れ':
            return 'sunny' if dtstr is None or 6 <= datetime.datetime.fromisoformat(dtstr).hour < 18 else 'clear-night'
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
#TODO 晴れか曇りの場合、降雨レーダーも参照する. とにかく降雨を逃さないように
print(pxl_color, weather )
vpfd=get_vpfd_data_pretty('130010')
fcst=get_forecast_data_pretty('130000','130010')
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
amedas_data['bunpu_weather'] = weather
amedas_data['forecast_hourly'] = fcst_h
amedas_data['forecast_daily'] = fcst_d
pub1 = mqtt_cli.publish(mqtt_topic_amedas_stat, weather, qos=1, retain=True)
pub2 = mqtt_cli.publish(mqtt_topic_amedas_attr, json.dumps(amedas_data), qos=1, retain=True)
pub3 = mqtt_cli.publish(mqtt_topic_amedas_avty, 'online', qos=1, retain=True)

#送信完了までプログラムを落とさないように待つ
pub1.wait_for_publish()
pub2.wait_for_publish()
pub3.wait_for_publish()

mqtt_cli.disconnect()
mqtt_cli.loop_stop()
from pprint import pprint
pprint(amedas_data)

