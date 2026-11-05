import os
import json
import math
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.colors import LinearSegmentedColormap
from matplotlib.ticker import MultipleLocator, FormatStrFormatter
from scipy.ndimage import gaussian_filter, sobel
import geopandas as gpd
from shapely.geometry import box, Point, Polygon, MultiPolygon

print("Starting taxonomy map generation...")

# Paths
data_dir = r"C:\Users\sures\.gemini\antigravity\scratch\india_taxonomy_map\data"
output_dir = r"C:\Users\sures\.gemini\antigravity\scratch\india_taxonomy_map\figures"
os.makedirs(output_dir, exist_ok=True)

# 1. Load DEMs
dem_south = np.load(os.path.join(data_dir, "dem_south_india.npy"))
with open(os.path.join(data_dir, "dem_south_india_meta.json"), "r") as f:
    meta_south = json.load(f)

dem_india = np.load(os.path.join(data_dir, "dem_india_all.npy"))
with open(os.path.join(data_dir, "dem_india_all_meta.json"), "r") as f:
    meta_india = json.load(f)

print(f"Loaded South India DEM {dem_south.shape}, bounds: Lon {meta_south['lon_left']:.2f}..{meta_south['lon_right']:.2f}, Lat {meta_south['lat_bottom']:.2f}..{meta_south['lat_top']:.2f}")

# 2. Load vector boundaries
states_gdf = gpd.read_file(os.path.join(data_dir, "india_states_clean.geojson"))
country_gdf = gpd.read_file(os.path.join(data_dir, "india_country_clean.geojson"))
districts_gdf = gpd.read_file(os.path.join(data_dir, "india_states_soi.geojson"))
ne_countries = gpd.read_file(os.path.join(data_dir, "ne_110m_countries.geojson"))
rivers_gdf = gpd.read_file(os.path.join(data_dir, "ne_10m_rivers.geojson"))

print(f"Loaded vectors: {len(states_gdf)} states, {len(districts_gdf)} districts, {len(rivers_gdf)} rivers.")

# Define study area bounds for Main Panel:
# South India: Lon 74.5°E to 80.8°E, Lat 8.0°N to 14.5°N
crop_lon_min, crop_lon_max = 74.4, 80.8
crop_lat_min, crop_lat_max = 8.0, 14.2

# Crop South India DEM to exact study area
# Transform lat/lon to pixel coordinates
def lon_to_px(lon, left, right, w):
    return int((lon - left) / (right - left) * w)

def lat_to_py(lat, top, bottom, h):
    # top has py=0, bottom has py=h
    return int((top - lat) / (top - bottom) * h)

h_s, w_s = dem_south.shape
px_min = max(0, lon_to_px(crop_lon_min, meta_south['lon_left'], meta_south['lon_right'], w_s))
px_max = min(w_s, lon_to_px(crop_lon_max, meta_south['lon_left'], meta_south['lon_right'], w_s))
py_min = max(0, lat_to_py(crop_lat_max, meta_south['lat_top'], meta_south['lat_bottom'], h_s))
py_max = min(h_s, lat_to_py(crop_lat_min, meta_south['lat_top'], meta_south['lat_bottom'], h_s))

dem_cropped = dem_south[py_min:py_max, px_min:px_max]
print(f"Cropped DEM: {dem_cropped.shape}, Lon {crop_lon_min}..{crop_lon_max}, Lat {crop_lat_min}..{crop_lat_max}")

# Filter slight noise and compute hillshade
dem_smooth = gaussian_filter(dem_cropped, sigma=1.0)

# Compute terrain slope and aspect for multi-directional hillshade
# Cell sizes in meters approximately at latitude ~11 degrees:
# 1 deg lat ~ 110.574 km, 1 deg lon ~ 111.320 * cos(11 deg) ~ 109.28 km
deg_lat_span = crop_lat_max - crop_lat_min
deg_lon_span = crop_lon_max - crop_lon_min
dy_m = (deg_lat_span * 110574.0) / dem_cropped.shape[0]
dx_m = (deg_lon_span * 109280.0) / dem_cropped.shape[1]

# Sobel derivatives
zy = sobel(dem_smooth, axis=0) / (8.0 * dy_m)
zx = sobel(dem_smooth, axis=1) / (8.0 * dx_m)

slope = np.arctan(np.sqrt(zx**2 + zy**2))
aspect = np.arctan2(-zy, zx)

def calc_hillshade(slope, aspect, alt_deg, az_deg):
    alt_rad = np.radians(alt_deg)
    az_rad = np.radians(az_deg)
    hs = np.sin(alt_rad) * np.cos(slope) + np.cos(alt_rad) * np.sin(slope) * np.cos(az_rad - aspect)
    return np.clip(hs, 0.0, 1.0)

# Multi-directional hillshade (classic Swiss cartography: 315° primary + 225° fill)
hs1 = calc_hillshade(slope, aspect, 45.0, 315.0)
hs2 = calc_hillshade(slope, aspect, 35.0, 225.0)
hillshade = 0.7 * hs1 + 0.3 * hs2
hillshade = (hillshade - hillshade.min()) / (hillshade.max() - hillshade.min() + 1e-5)

# Hypsometric colormap for scientific botany/zoology
# Coastal plains (green) -> midlands (ochre/amber) -> high Western Ghats (sienna/burnt umber/dark alpine)
colors_hyps = [
    (0.00, '#a1d99b'),  #   0 - 50m (pale coastal green)
    (0.04, '#c7e9c0'),  #  50 - 100m
    (0.12, '#edf8b1'),  # 100 - 300m (gentle plain yellow-green)
    (0.24, '#fed976'),  # 300 - 600m (plateau warm ochre)
    (0.40, '#feb24c'),  # 600 - 1000m (foothills amber)
    (0.60, '#fd8d3c'),  # 1000 - 1500m (mid-elevation mountain)
    (0.76, '#e6550d'),  # 1500 - 2000m (high range sienna)
    (0.90, '#a63603'),  # 2000 - 2400m (steep ridge umber)
    (1.00, '#4a1400')   # 2400 - 2695m (highest peaks dark chocolate)
]
cmap_hyp = LinearSegmentedColormap.from_list('taxonomy_hyps', [(pos, col) for pos, col in colors_hyps], N=256)

# Normalize land elevation (0 to 2600m)
elev_clamped = np.clip(dem_cropped, 0.0, 2600.0)
norm_elev = elev_clamped / 2600.0
rgb_hyp = cmap_hyp(norm_elev)[:, :, :3]

# Blend hypsometric colors with hillshade (soft light / multiply formula)
# Brightness enhancement for clean journal print
hs_factor = 0.40 + 0.60 * hillshade[:, :, np.newaxis]
blended_land = np.clip(rgb_hyp * hs_factor * 1.15, 0.0, 1.0)

# Mask ocean areas (dem <= 0)
is_sea = (dem_cropped <= 0.0)
# Clean oceanic bathymetric blue
sea_color = np.array([219/255.0, 234/255.0, 248/255.0]) # #dbeaf8
final_raster = np.where(is_sea[:, :, np.newaxis], sea_color[np.newaxis, np.newaxis, :], blended_land)

print(f"Rendered final relief raster: {final_raster.shape}")

# Save raster image for verification
from PIL import Image
im_relief = Image.fromarray((final_raster * 255).astype(np.uint8))
im_relief.save(os.path.join(output_dir, "test_relief_canvas.png"))
print("Saved test_relief_canvas.png")

