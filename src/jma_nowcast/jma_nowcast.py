import os
import math

from typing import List, Tuple, Dict, Set, Any
from pprint import pprint
from io import BytesIO
import copy

from PIL import Image
import requests

from jma_common import fetch_json

_DEBUG_ADDRESS_=False
_DEBUG_STORE_IMG_=False


# memo
# L0   0mm 255,255,255,  0    0,  0,100 白（ただし透明） ←HSV　色相 彩度 明度
# L1 ~ 5mm 242,242,255,255  240,  5,100 限りなく白に近い水色
# L2 ~10mm 160,210,255,255  208, 37,100 薄い水色
# L3 ~20mm  33,140,255,255  211, 87,100 ほぼ青(濃い水色)
# L4 ~30mm 250,245,  0,255  き
# L5 ~50mm 255,153,  0,255 だいだい
# L6 ~80mm 255, 40,  0,255 あか
# L7 ~xxmm 180,  0,104,255 あずき
level_by_color={
    (  0,  0,  0,  0):0,
    (255,255,255,  0):0,
    (242,242,255,255):1,
    (160,210,255,255):2,
    ( 33,140,255,255):3,
    (  0, 65,255,255):4,
    (250,245,  0,255):5,
    (255,153,  0,255):6,
    (255, 40,  0,255):7,
    (180,  0,104,255):8,
}
amount_str_by_level={
    0:'0mm',
    1:'1mm/h未満',
    2:'1-5mm/h',
    3:'5-10mm/h',
    4:'10-20mm/h',
    5:'20-30mm/h',
    6:'30-50mm/h',
    7:'50-80mm/h',
    8:'80mm/h以上',
}
amount_by_level={
    0:(0,0),
    1:(0,1),
    2:(1,5),
    3:(5,10),
    4:(10,20),
    5:(20,30),
    6:(30,50),
    7:(50,80),
    8:(80,200),#200 は過去の日本最高記録(公式153非公式187)を想定した適当な値
}


def latlng_to_tile_pixel(lat, lng, zoom):
    lat_rad = math.radians(lat)
    n = 2 ** zoom
    x = (lng + 180.0) / 360.0
    y = (1.0 - math.log(math.tan(lat_rad) + 1 / math.cos(lat_rad)) / math.pi) / 2.0

    tile_x = int(x * n)
    tile_y = int(y * n)
    pixel_x = int((x * n * 256) % 256)
    pixel_y = int((y * n * 256) % 256)

    return tile_x, tile_y, pixel_x, pixel_y


def load_image_url(url):
    print(url)
    resp_img = requests.get(url)
    print(f'{resp_img.status_code} {resp_img.reason}')
    resp_img.raise_for_status()
    img_raw = Image.open(BytesIO(resp_img.content))
    # パレットモードのような挙動を示ことがある(getpixelの戻りが単一の数字になる)ので明示的にRGBAにコンバートする
    img_cnv = img_raw.convert('RGBA')
    return img_cnv

def load_rain_image_one(lvl: int, tilex: int, tiley: int, basetime: str, validtime: str) -> Image:
    url=f'https://www.jma.go.jp/bosai/jmatile/data/nowc/{basetime}/none/{validtime}/surf/hrpns/{lvl}/{tilex}/{tiley}.png'
    return load_image_url(url)


def get_nowc_forecast(lat,lon,zoom=10):
    if zoom>14:
        raise ValueError('Zoomレベルは4から14の間で指定してください')
    elif zoom>=10:
        rain_zoom=10
    elif zoom>=8:
        rain_zoom=8
    elif zoom>=6:
        rain_zoom=6
    elif zoom>=4:
        rain_zoom=4
    else :
        raise ValueError('Zoomレベルは4から14の間で指定してください')

    rain_tile_x, rain_tile_y, rain_pxl_x, rain_pxl_y = latlng_to_tile_pixel(lat, lon, rain_zoom)
    # print(
    #     f'{rain_zoom=}\n'
    #     f'{rain_tile_x=}\n'
    #     f'{rain_tile_y=}\n'
    #     f'{rain_pxl_x=}\n'
    #     f'{rain_pxl_y=}\n'
    # )

    # N1 過去のタイムライン basetimeとvalidtimeは同じ elementsにhrpnsが含まれる(降雨ナウキャスト)
    # N2 basetimeはN1の最新と同じ(N2が更新が遅く1世代前のこともある)、validtimeがbasetimeの未来時刻で5分間隔で60分後まで(１２枚)
    # N3 elementsがその他諸々（雷とか）
    nowc_json1 = fetch_json('https://www.jma.go.jp/bosai/jmatile/data/nowc/targetTimes_N1.json')
    nowc_json2 = fetch_json('https://www.jma.go.jp/bosai/jmatile/data/nowc/targetTimes_N2.json')
    nowc_current = max(nowc_json1, key=lambda x: int(x['validtime']))
    nowc_times = copy.deepcopy(nowc_json2)
    nowc_times.append(nowc_current)
    nowc_times.sort(key=lambda x:(-int(x['basetime']),int(x['validtime'])))

    colors=[]
    levels=[]
    amounts=[]
    for _t in nowc_times:
        rain_load=load_rain_image_one(rain_zoom, rain_tile_x,rain_tile_y,_t['basetime'], _t['validtime'])
        if _DEBUG_STORE_IMG_:
            rain_load.save(f'./rain_load_{_t["basetime"]}_{_t["validtime"]}_{rain_zoom}_{rain_tile_x}_{rain_tile_y}.png')
        px=rain_load.getpixel((rain_pxl_x,rain_pxl_y,))
        colors.append(px)
        if px[3] == 0:
            lvl = 0
        else:
            lvl = level_by_color[px]
        levels.append(lvl)
        amounts.append(amount_by_level[lvl])
    ret = [(
        _x[0]['validtime'],
        'observation' if _i==0 else 'forecast',
        _x[1],
        _x[2][0],
        _x[2][1],
        )for _i,_x in enumerate(zip(nowc_times,levels,amounts))
    ]
    return ret


if __name__ == '__main__':
    import dotenv
    dotenv.load_dotenv()
    map_lat=float(os.environ['NOWCAST_RAIN_LAT'])
    map_lon=float(os.environ['NOWCAST_RAIN_LNG'])
    map_zoom=int(os.environ['NOWCAST_RAIN_ZOOM'])
    nowc_forecast = get_nowc_forecast(map_lat, map_lon, zoom=map_zoom)




