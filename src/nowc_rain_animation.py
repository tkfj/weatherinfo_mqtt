import os
from jma_nowcast import load_and_save_nowc_forecast_images

map_lat=float(os.environ['NOWCAST_RAIN_LAT'])
map_lon=float(os.environ['NOWCAST_RAIN_LON'])
map_zoom=int(os.environ['NOWCAST_RAIN_ZOOM'])
map_range=int(os.environ['NOWCAST_RAIN_RADAR_RANGE'])

load_and_save_nowc_forecast_images('./animated.png',map_lat,map_lon,map_range,lvl=map_zoom)
