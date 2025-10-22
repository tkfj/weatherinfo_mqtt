"""
推計気象分布
https://www.data.jma.go.jp/bunpu/
"""
import datetime
import operator

from jma_common import fetch_text,fetch_image,get_sunny_or_clear_night

def _center_score_euclid(x, y, w, h):
    """
    ユークリッド距離を求める
    """
    a, b = w/2, h/2
    d = ((x-a)**2 + (y-b)**2) ** 0.5
    dmax = (a*a + b*b) ** 0.5
    return max(0.0, 1.0 - d/dmax)

def _bunpu_areas_parse_line(line):
    """
    bunpu_areasの行をパースする
    """
    code,token1=line.split('=',1)
    token1 = token1.strip('&') #まれにゴミがついている
    dic = {
        _k.replace('\\',''):float(_v)
        for _k, _v in [token2.split('\\=',1) for token2 in token1.split('&') if len(token2)>0]
    }
    dic['code'] = code
    dic['lvl'] = 1 if code=='000' else len(code)
    return dic

def get_bunpu_area_coordinates(lat:float, lon:float) -> tuple:
    """
    緯度経度から推計気象分布の地図座標を求める
    """
    bunpu_areas_raw = fetch_text('https://www.data.jma.go.jp/bunpu//js/area.properties')
    bunpu_areas = [
        _bunpu_areas_parse_line(_x)
        for _x
        in map(lambda _y:_y.strip(), bunpu_areas_raw.splitlines())
        if len(_x)>0 and not _x.startswith('#')
    ]

    for rect in bunpu_areas:
        rect['x'] = (lon-rect['posW'])/(rect['posE']-rect['posW'])
        rect['y'] = (rect['posN']-lat)/(rect['posN']-rect['posS'])
        # 最も中央に近いものを採用するため、ユークリッド距離を求める
        rect['s'] = _center_score_euclid(rect['x'],rect['y'],1,1)

    # 解像度が高いマップの中で最も中央に近いものを選択
    selected = sorted(bunpu_areas, key=operator.itemgetter('lvl', 's'), reverse=True)[0]

    # マップ画像を取得し、そのサイズからピクセル位置を特定する
    img=fetch_image(f'https://www.data.jma.go.jp/bunpu/img/munic/munic_{selected["code"]}.png')
    px=int(selected['x'] * img.width)
    py=int(selected['y'] * img.height)
    return selected['code'], px, py

def get_bunpu_weather(tile_cd:str, px:int, py:int, dt:datetime):
    """
    推計気象分布の地図から地点の天気を返す
    """
    while True: # 最新の時刻が提供されないので、見つかるまで遡り続ける
        # TODO リミッター
        dt_s = dt.strftime('%Y%m%d%H')+'00'
        img = fetch_image(f'https://www.data.jma.go.jp/bunpu/img/wthr/{tile_cd}/wthr_{tile_cd}_{dt_s}.png', raise_error=False)
        # ご参考：
        # 地形地図： https://www.data.jma.go.jp/bunpu/img/bgmap/bg_{tile_cd}.jpg
        # 行政地図： https://www.data.jma.go.jp/bunpu/img/munic/munic_{tile_cd}.png
        if img is not None:
            break
        dt = dt - datetime.timedelta(hours=1)
    pxl_color=img.getpixel((px,py))
    match pxl_color:
        case (0xff, 0xaa, 0x00, 0xff):
            return get_sunny_or_clear_night(dt)
        case (0xaa, 0xaa, 0xaa, 0xff):
            return 'cloudy'
        case (0x00, 0x41, 0xff, 0xff):
            return 'rainy'
        case (0xf2, 0xf2, 0xff, 0xff):
            return 'snowy'
        case (0xa0, 0xd2, 0xff, 0xff):
            return 'snowy-rainy'
        case _:
            return 'unknown'

if __name__ == '__main__':
    import os
    import dotenv
    dotenv.load_dotenv()
    map_lat=float(os.environ['NOWCAST_RAIN_LAT'])
    map_lon=float(os.environ['NOWCAST_RAIN_LNG'])
    # sapporo station
    # map_lat=43.0685983
    # map_lon=141.3507201

    (cd,x,y) = get_bunpu_area_coordinates(map_lat,map_lon)
    print((cd,x,y))
    weather = get_bunpu_weather(cd, x, y, datetime.datetime.now())
    print(weather)
