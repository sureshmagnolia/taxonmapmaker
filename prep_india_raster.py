import os
import json
import numpy as np
from scipy.ndimage import gaussian_filter, sobel
from matplotlib.colors import LinearSegmentedColormap
from PIL import Image

data_dir = r"C:\Users\sures\.gemini\antigravity\scratch\india_taxonomy_map\data"
dem_india = np.load(os.path.join(data_dir, "dem_india_all.npy"))
with open(os.path.join(data_dir, "dem_india_all_meta.json"), "r") as f:
    meta_india = json.load(f)

print(f"dem_india: shape={dem_india.shape}, min={dem_india.min()}, max={dem_india.max()}")

dem_smooth = gaussian_filter(dem_india, sigma=1.0)

# Approx resolution in meters across India (~lat 22)
dy_m = ((meta_india['lat_top'] - meta_india['lat_bottom']) * 110574.0) / dem_india.shape[0]
dx_m = ((meta_india['lon_right'] - meta_india['lon_left']) * 111320.0 * np.cos(np.radians(22))) / dem_india.shape[1]

zy = sobel(dem_smooth, axis=0) / (8.0 * dy_m)
zx = sobel(dem_smooth, axis=1) / (8.0 * dx_m)

slope = np.arctan(np.sqrt(zx**2 + zy**2))
aspect = np.arctan2(-zy, zx)

def calc_hs(slope, aspect, alt_deg, az_deg):
    alt_rad = np.radians(alt_deg)
    az_rad = np.radians(az_deg)
    return np.clip(np.sin(alt_rad)*np.cos(slope) + np.cos(alt_rad)*np.sin(slope)*np.cos(az_rad - aspect), 0, 1)

hs = 0.7 * calc_hs(slope, aspect, 45, 315) + 0.3 * calc_hs(slope, aspect, 35, 225)
hs = (hs - hs.min()) / (hs.max() - hs.min() + 1e-5)

colors_hyps = [
    (0.00, '#a1d99b'),
    (0.05, '#c7e9c0'),
    (0.12, '#edf8b1'),
    (0.25, '#fed976'),
    (0.40, '#feb24c'),
    (0.55, '#fd8d3c'),
    (0.70, '#e6550d'),
    (0.85, '#a63603'),
    (1.00, '#f7f4f9')   # snow on high Himalayas
]
cmap = LinearSegmentedColormap.from_list('india_hyps', [(p, c) for p, c in colors_hyps], N=256)

elev_c = np.clip(dem_india, 0, 7500)
rgb = cmap(elev_c / 7500.0)[:, :, :3]
hs_factor = 0.35 + 0.65 * hs[:, :, np.newaxis]
blended = np.clip(rgb * hs_factor * 1.15, 0, 1)

is_sea = (dem_india <= 0.0)
sea_col = np.array([219/255.0, 234/255.0, 248/255.0])
final_india_raster = np.where(is_sea[:, :, np.newaxis], sea_col[np.newaxis, np.newaxis, :], blended)

np.save(os.path.join(data_dir, "raster_india_all.npy"), final_india_raster)
print("Saved raster_india_all.npy successfully!")

