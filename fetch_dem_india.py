import os
import math
import requests
from PIL import Image
import numpy as np

def latlon_to_tile(lat, lon, zoom):
    lat_rad = math.radians(lat)
    n = 2.0 ** zoom
    xtile = int((lon + 180.0) / 360.0 * n)
    ytile = int((1.0 - math.asinh(math.tan(lat_rad)) / math.pi) / 2.0 * n)
    return xtile, ytile

def tile_to_latlon(xtile, ytile, zoom):
    n = 2.0 ** zoom
    lon = xtile / n * 360.0 - 180.0
    lat_rad = math.atan(math.sinh(math.pi * (1.0 - 2.0 * ytile / n)))
    lat = math.degrees(lat_rad)
    return lat, lon

cache_dir = r"C:\Users\sures\.gemini\antigravity\scratch\india_taxonomy_map\data\cache_tiles"
os.makedirs(cache_dir, exist_ok=True)

zoom = 6
# All India: Lat 6.0 to 37.5, Lon 67.5 to 98.0
x1, y1 = latlon_to_tile(37.5, 67.5, zoom)
x2, y2 = latlon_to_tile(6.0, 98.0, zoom)

width = (x2 - x1 + 1) * 256
height = (y2 - y1 + 1) * 256
elev_grid = np.zeros((height, width), dtype=np.float32)

print(f"Fetching all-India tiles zoom {zoom}: x={x1}..{x2}, y={y1}..{y2} ({width}x{height})")

sess = requests.Session()
sess.headers.update({'User-Agent': 'TaxonomyMapBuilder/1.0'})

for y in range(y1, y2 + 1):
    for x in range(x1, x2 + 1):
        tile_path = os.path.join(cache_dir, f"{zoom}_{x}_{y}.png")
        if not os.path.exists(tile_path):
            url = f"https://s3.amazonaws.com/elevation-tiles-prod/terrarium/{zoom}/{x}/{y}.png"
            r = sess.get(url, timeout=10)
            if r.status_code == 200:
                with open(tile_path, 'wb') as f:
                    f.write(r.content)
            else:
                print(f"Failed tile {x},{y}: status {r.status_code}")
                continue
        
        im = Image.open(tile_path).convert('RGB')
        arr = np.array(im, dtype=np.float32)
        elev = (arr[:, :, 0] * 256.0 + arr[:, :, 1] + arr[:, :, 2] / 256.0) - 32768.0
        
        iy = (y - y1) * 256
        ix = (x - x1) * 256
        elev_grid[iy:iy+256, ix:ix+256] = elev

lat_top, lon_left = tile_to_latlon(x1, y1, zoom)
lat_bottom, lon_right = tile_to_latlon(x2 + 1, y2 + 1, zoom)

print(f"All-India DEM shape: {elev_grid.shape}")
print(f"Bounds: Lon {lon_left:.4f} to {lon_right:.4f}, Lat {lat_bottom:.4f} to {lat_top:.4f}")
print(f"Elevation min={np.min(elev_grid):.1f}m, max={np.max(elev_grid):.1f}m")

np.save(r"C:\Users\sures\.gemini\antigravity\scratch\india_taxonomy_map\data\dem_india_all.npy", elev_grid)
meta = {
    'lon_left': lon_left,
    'lon_right': lon_right,
    'lat_top': lat_top,
    'lat_bottom': lat_bottom,
    'zoom': zoom,
    'shape': list(elev_grid.shape)
}
import json
with open(r"C:\Users\sures\.gemini\antigravity\scratch\india_taxonomy_map\data\dem_india_all_meta.json", 'w') as f:
    json.dump(meta, f)
print("Saved dem_india_all.npy successfully!")

