"""
ナウキャスト
https://www.jma.go.jp/bosai/nowc/
"""
import os
import math

from typing import List, Tuple, Dict, Set, Any
from pprint import pprint
from io import BytesIO
import copy

from PIL import Image

from jma_common import fetch_json, fetch_binary

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


def latlon_to_tile_pixel(lat, lon, lvl):
    lat_rad = math.radians(lat)
    n = 2 ** lvl
    x = (lon + 180.0) / 360.0
    y = (1.0 - math.log(math.tan(lat_rad) + 1 / math.cos(lat_rad)) / math.pi) / 2.0

    tile_x = int(x * n)
    tile_y = int(y * n)
    pixel_x = int((x * n * 256) % 256)
    pixel_y = int((y * n * 256) % 256)

    return tile_x, tile_y, pixel_x, pixel_y


def tile_pixel_to_latlon(tile_x, tile_y, pixel_x, pixel_y, lvl):
    n = 2 ** lvl
    gx = tile_x * 256 + pixel_x
    gy = tile_y * 256 + pixel_y

    x = gx / (256.0 * n)
    y = gy / (256.0 * n)

    lon = x * 360.0 - 180.0
    lat_rad = math.atan(math.sinh(math.pi * (1.0 - 2.0 * y)))
    lat = math.degrees(lat_rad)
 
    return lat,lon

def meters_per_pixel(lat, lvl):
    # マジックナンバーは赤道の距離を256で割ったもの
    return (156543.03392 * math.cos(math.radians(lat))) / (2 ** lvl)

def load_image_url(url):
    binary:bytes = fetch_binary(url)
    img_raw = Image.open(BytesIO(binary))
    # パレットモードのような挙動を示ことがある(getpixelの戻りが単一の数字になる)ので明示的にRGBAにコンバートする
    img_cnv = img_raw.convert('RGBA')
    return img_cnv

def load_base_image_one(lvl: int, tilex: int, tiley: int) -> Image.Image:
    url = f'https://www.jma.go.jp/tile/gsi/pale/{lvl}/{tilex}/{tiley}.png'
    img = load_image_url(url)
    if _DEBUG_STORE_IMG_:
        img.save(f'./base_img_{lvl}_{tilex}_{tiley}.png')
    return img

def load_base_image_join(lvl: int, lat:float, lon: float, radius_meter: int) -> Image.Image:
    img = load_image_join(lvl, lat, lon, radius_meter, lambda lvl,x,y : load_base_image_one(lvl,x,y))
    if _DEBUG_STORE_IMG_:
        img.save(f'./base_img_join_{lvl}.png')
    return img

def load_rain_image_one(lvl: int, tilex: int, tiley: int, basetime: str, validtime: str) -> Image.Image:
    url=f'https://www.jma.go.jp/bosai/jmatile/data/nowc/{basetime}/none/{validtime}/surf/hrpns/{lvl}/{tilex}/{tiley}.png'
    img = load_image_url(url)
    if _DEBUG_STORE_IMG_:
        img.save(f'./rain_img_{lvl}_{tilex}_{tiley}_{basetime}_{validtime}.png')
    return load_image_url(url)

def load_rain_image_join(lvl: int, lat:float, lon: float, radius_meter: int, basetime: str, validtime: str) -> Image.Image:
    img = load_image_join(lvl, lat, lon, radius_meter, lambda lvl,x,y : load_rain_image_one(lvl,x,y,basetime,validtime))
    if _DEBUG_STORE_IMG_:
        img.save(f'./rain_img_join_{lvl}_{basetime}_{validtime}.png')
    return img

def get_rain_images_join_forecast(lat,lon,radius_meter,lvl=10):
    nowc_times = get_nowc_forecast_times()
    return [load_rain_image_join(lvl,lat,lon,radius_meter,_t['basetime'],_t['validtime']) for _t in nowc_times]

def load_image_join(lvl: int, lat:float, lon: float, radius_meter: int, load_one_func) -> Image.Image:
    print(lvl,lat,lon,radius_meter)
    tx0,ty0,px0,py0 = latlon_to_tile_pixel(lat,lon,lvl)
    mpp = meters_per_pixel(lat,lvl)
    pxls = int(radius_meter / mpp)
    gx1 = tx0 * 256 + px0 - pxls
    gy1 = ty0 * 256 + py0 - pxls
    gx2 = tx0 * 256 + px0 + pxls
    gy2 = ty0 * 256 + py0 + pxls
    tx1, px1 = divmod(gx1, 256)
    ty1, py1 = divmod(gy1, 256)
    tx2, px2 = divmod(gx2, 256)
    ty2, py2 = divmod(gy2, 256)
    img_join = Image.new("RGBA", ((tx2-tx1+1)*256,(ty2-ty1+1)*256))
    for x in range(tx1, tx2+1):
        for y in range(ty1, ty2+1):
            img_one = load_one_func(lvl,x,y)
            img_join.paste(img_one,((x-tx1)*256,(y-ty1)*256))
    img_crop = img_join.crop((
        px1,
        py1,
        (tx2-tx1)*256+px2,
        (ty2-ty1)*256+py2,
    ))
    return img_crop

def get_rain_zoom(lvl):
    "降雨レーダーのズームレベルは4,6,8,10のみ"
    if lvl>14:
        raise ValueError('Zoomレベルは4から14の間で指定してください')
    elif lvl>=10:
        rain_lvl=10
    elif lvl>=8:
        rain_lvl=8
    elif lvl>=6:
        rain_lvl=6
    elif lvl>=4:
        rain_lvl=4
    else:
        raise ValueError('Zoomレベルは4から14の間で指定してください')
    return rain_lvl

def get_nowc_forecast_times():
    # N1 過去のタイムライン basetimeとvalidtimeは同じ elementsにhrpnsが含まれる(降雨ナウキャスト)
    # N2 basetimeはN1の最新と同じ(N2が更新が遅く1世代前のこともある)、validtimeがbasetimeの未来時刻で5分間隔で60分後まで(１２枚)
    # N3 elementsがその他諸々（雷とか）
    nowc_json1 = fetch_json('https://www.jma.go.jp/bosai/jmatile/data/nowc/targetTimes_N1.json')
    nowc_json2 = fetch_json('https://www.jma.go.jp/bosai/jmatile/data/nowc/targetTimes_N2.json')
    nowc_current = max(nowc_json1, key=lambda x: int(x['validtime']))
    nowc_times = copy.deepcopy(nowc_json2)
    nowc_times.append(nowc_current)
    nowc_times.sort(key=lambda x:(-int(x['basetime']),int(x['validtime'])))
    return nowc_times

def get_nowc_forecast(lat,lon,zoom=10):
    rain_zoom = get_rain_zoom(zoom)

    rain_tile_x, rain_tile_y, rain_pxl_x, rain_pxl_y = latlon_to_tile_pixel(lat, lon, rain_zoom)

    nowc_times = get_nowc_forecast_times()

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

def rain_composite(base_img, rain_img):
    resized_img = rain_img.resize((base_img.width, base_img.height), resample=Image.BOX)
    rain_composite = Image.composite(
        resized_img, base_img,
        Image.eval(resized_img.getchannel('A'), lambda a: 0xCC if a > 0 else 0x33)
    )
    return rain_composite

def get_nowc_forecast_images(lat,lon,radius_meter,lvl=10):
    rain_lvl = get_rain_zoom(lvl)
    base_img = load_base_image_join(lvl,lat,lon, radius_meter)
    rain_imgs = get_rain_images_join_forecast(lat,lon, radius_meter, lvl=rain_lvl)
    composite_imgs = [rain_composite(base_img, _img) for _img in rain_imgs]
    return composite_imgs

def load_and_save_nowc_forecast_images(path, lat,lon,radius_meter,lvl=10, duration_base:int=2000, duration_rest:int=500, loop:int=0):
    imgs = get_nowc_forecast_images(lat,lon,radius_meter,lvl)
    save_ani_png(path,imgs,duration_base,duration_rest,loop)

def save_ani_png(path:str, imgs:List[Image.Image], duration_base:int=2000, duration_rest:int=500, loop:int=0):
    ani_base, ani_rest = imgs[0], imgs[1:]
    ani_base.save(
        path,
        format='PNG',
        save_all = True,
        append_images = ani_rest,
        duration = [duration_base, *([duration_rest]*len(ani_rest))],
        loop = loop,
        disposal = 0,
        blend = 0,
        default_image = False,
    )


if __name__ == '__main__':
    import dotenv
    dotenv.load_dotenv()
    map_lat=float(os.environ['NOWCAST_RAIN_LAT'])
    map_lon=float(os.environ['NOWCAST_RAIN_LON'])
    map_zoom=int(os.environ['NOWCAST_RAIN_ZOOM'])
    # nowc_forecast = get_nowc_forecast(map_lat, map_lon, lvl=map_zoom)
    load_and_save_nowc_forecast_images('./animated.png',map_lat,map_lon,10_000,lvl=map_zoom)
