import math
import requests
from PIL import Image
import io

def latlon_to_tile(lat, lon, zoom):
    lat_rad = math.radians(lat)
    n = 2.0 ** zoom
    xtile = int((lon + 180.0) / 360.0 * n)
    ytile = int((1.0 - math.asinh(math.tan(lat_rad)) / math.pi) / 2.0 * n)
    return xtile, ytile

def get_elevation(lat, lon, zoom=10):
    xtile, ytile = latlon_to_tile(lat, lon, zoom)
    url = f"https://s3.amazonaws.com/elevation-tiles-prod/terrarium/{zoom}/{xtile}/{ytile}.png"
    r = requests.get(url, timeout=10)
    if r.status_code != 200:
        return None
    img = Image.open(io.BytesIO(r.content))
    n = 2.0 ** zoom
    x_exact = (lon + 180.0) / 360.0 * n
    lat_rad = math.radians(lat)
    y_exact = (1.0 - math.asinh(math.tan(lat_rad)) / math.pi) / 2.0 * n
    px = int((x_exact - xtile) * 256)
    py = int((y_exact - ytile) * 256)
    px = max(0, min(255, px))
    py = max(0, min(255, py))
    r_val, g_val, b_val = img.getpixel((px, py))[:3]
    elevation = (r_val * 256.0 + g_val + b_val / 256.0) - 32768.0
    return elevation

elev1 = get_elevation(10.7870, 79.1378, zoom=10)
elev2 = get_elevation(11.067917, 76.56025, zoom=10)
print(f"Point 1 Elevation: {elev1:.1f} m")
print(f"Point 2 Elevation: {elev2:.1f} m")

