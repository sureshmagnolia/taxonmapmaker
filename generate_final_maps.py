import os
import json
import math
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.patches import Polygon as MplPolygon, FancyBboxPatch, Rectangle, PathPatch
from matplotlib.path import Path
from matplotlib.colors import LinearSegmentedColormap
import geopandas as gpd
from shapely.geometry import box, Point, Polygon, MultiPolygon
from scipy.ndimage import gaussian_filter, sobel

# Set publication style
matplotlib.rcParams.update({
    'font.family': 'sans-serif',
    'font.sans-serif': ['Arial', 'DejaVu Sans', 'Liberation Sans'],
    'font.size': 10,
    'axes.labelsize': 10,
    'xtick.labelsize': 9,
    'ytick.labelsize': 9,
    'pdf.fonttype': 42,
    'svg.fonttype': 'none',
    'figure.dpi': 300,
    'savefig.dpi': 300,
})

data_dir = r"C:\Users\sures\.gemini\antigravity\scratch\india_taxonomy_map\data"
out_dir = r"C:\Users\sures\.gemini\antigravity\scratch\india_taxonomy_map\figures"
os.makedirs(out_dir, exist_ok=True)

print("Loading high-resolution spatial datasets...")
# 1. High-resolution boundaries
# India official composite SOI boundary (252,604 vertices)
india_highres_gdf = gpd.read_file(os.path.join(data_dir, "india-composite.geojson"))

# India state boundaries (clean)
states_gdf = gpd.read_file(os.path.join(data_dir, "india_states_clean.geojson"))
districts_gdf = gpd.read_file(os.path.join(data_dir, "india_states_soi.geojson"))

# 10m Land for Sri Lanka and islands (105,000+ vertices)
land_10m_gdf = gpd.read_file(os.path.join(data_dir, "ne_10m_land.geojson"))

# 10m Rivers
rivers_gdf = gpd.read_file(os.path.join(data_dir, "ne_10m_rivers.geojson"))

# 110m countries for distant neighbors
ne_countries = gpd.read_file(os.path.join(data_dir, "ne_110m_countries.geojson"))

# 2. Elevation rasters
dem_south = np.load(os.path.join(data_dir, "dem_south_india.npy"))
with open(os.path.join(data_dir, "dem_south_india_meta.json"), "r") as f:
    meta_south = json.load(f)

raster_india = np.load(os.path.join(data_dir, "raster_india_all.npy"))
with open(os.path.join(data_dir, "dem_india_all_meta.json"), "r") as f:
    meta_india = json.load(f)

# Coordinates
loc1_lon, loc1_lat = 79.1378, 10.7870
loc2_lon, loc2_lat = 76.56025, 11.067917

# Study area limits
lon_min, lon_max = 74.4, 80.8
lat_min, lat_max = 8.0, 14.2
study_box = box(lon_min, lat_min, lon_max, lat_max)

# Extract Sri Lanka 10m high-resolution land
sl_box = box(79.0, 7.8, 82.5, 10.5)
sl_land_10m = land_10m_gdf[land_10m_gdf.intersects(sl_box)].clip(study_box)

# Extract India land from 252k-vertex SOI composite
india_study = india_highres_gdf.clip(study_box)

# Helper: Convert Shapely Polygon/MultiPolygon to Matplotlib Path
def shapely_to_mpl_path(geom):
    if geom is None or geom.is_empty:
        return None
    if geom.geom_type == 'Polygon':
        polys = [geom]
    elif geom.geom_type == 'MultiPolygon':
        polys = list(geom.geoms)
    elif geom.geom_type == 'GeometryCollection':
        polys = [g for g in geom.geoms if g.geom_type in ('Polygon', 'MultiPolygon')]
        expanded = []
        for p in polys:
            if p.geom_type == 'MultiPolygon':
                expanded.extend(list(p.geoms))
            else:
                expanded.append(p)
        polys = expanded
    else:
        return None
    
    verts = []
    codes = []
    for poly in polys:
        if poly.is_empty:
            continue
        ext = np.asarray(poly.exterior.coords)
        if len(ext) < 3:
            continue
        verts.extend(ext)
        codes.append(Path.MOVETO)
        codes.extend([Path.LINETO] * (len(ext) - 2))
        codes.append(Path.CLOSEPOLY)
        for interior in poly.interiors:
            inte = np.asarray(interior.coords)
            if len(inte) < 3:
                continue
            verts.extend(inte)
            codes.append(Path.MOVETO)
            codes.extend([Path.LINETO] * (len(inte) - 2))
            codes.append(Path.CLOSEPOLY)
    if not verts:
        return None
    return Path(verts, codes)

# Combined land geometry (India + Sri Lanka) in study area for vector clipping
combined_land_geom = india_study.geometry.union_all().union(sl_land_10m.geometry.union_all())
land_path = shapely_to_mpl_path(combined_land_geom)

print(f"Combined land path created with {len(land_path.vertices)} vertices!")

# Crop South India DEM
h_s, w_s = dem_south.shape
def lon_to_px(lon, left, right, w): return int((lon - left) / (right - left) * w)
def lat_to_py(lat, top, bottom, h): return int((top - lat) / (top - bottom) * h)

px_min = lon_to_px(lon_min, meta_south['lon_left'], meta_south['lon_right'], w_s)
px_max = lon_to_px(lon_max, meta_south['lon_left'], meta_south['lon_right'], w_s)
py_min = lat_to_py(lat_max, meta_south['lat_top'], meta_south['lat_bottom'], h_s)
py_max = lat_to_py(lat_min, meta_south['lat_top'], meta_south['lat_bottom'], h_s)

dem_crop = dem_south[py_min:py_max, px_min:px_max]
dem_smooth = gaussian_filter(dem_crop, sigma=1.0)

# Multi-directional hillshade
deg_lat_span = lat_max - lat_min
deg_lon_span = lon_max - lon_min
dy_m = (deg_lat_span * 110574.0) / dem_crop.shape[0]
dx_m = (deg_lon_span * 109280.0) / dem_crop.shape[1]

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
    (0.04, '#c7e9c0'),
    (0.12, '#edf8b1'),
    (0.24, '#fed976'),
    (0.40, '#feb24c'),
    (0.60, '#fd8d3c'),
    (0.76, '#e6550d'),
    (0.90, '#a63603'),
    (1.00, '#4a1400')
]
cmap_hyp = LinearSegmentedColormap.from_list('tax_hyps', [(p, c) for p, c in colors_hyps], N=256)

elev_c = np.clip(dem_crop, 0, 2600)
rgb_hyp = cmap_hyp(elev_c / 2600.0)[:, :, :3]
hs_factor = 0.40 + 0.60 * hs[:, :, np.newaxis]
blended_land = np.clip(rgb_hyp * hs_factor * 1.15, 0, 1)

print("Starting Master Figure plotting...")

# -------------------------------------------------------------
# CREATE MASTER FIGURE
# -------------------------------------------------------------
fig = plt.figure(figsize=(11.5, 12.0), facecolor='white')

# Main Map Axis [left, bottom, width, height]
ax_main = fig.add_axes([0.08, 0.08, 0.88, 0.86])
ax_main.set_facecolor('#dbeaf8') # Smooth uniform oceanic blue background

# 1. Render relief raster clipped with vector precision to the smooth land outline
im_land = ax_main.imshow(
    blended_land,
    extent=[lon_min, lon_max, lat_min, lat_max],
    origin='upper',
    interpolation='bicubic',
    zorder=2
)

# Apply vector clip path to make the land/ocean transition silky smooth
clip_patch = PathPatch(land_path, facecolor='none', edgecolor='none', transform=ax_main.transData)
ax_main.add_patch(clip_patch)
im_land.set_clip_path(clip_patch)

# 2. Render smooth vector coastlines
# India coastline (Survey of India official boundary - 6,953 vertices)
india_study.boundary.plot(ax=ax_main, color='#262626', linewidth=1.1, zorder=5)

# Sri Lanka smooth 10m coastline (thousands of vertices)
sl_land_10m.boundary.plot(ax=ax_main, color='#444444', linewidth=1.0, zorder=5)

# 3. Render District Boundaries (subtle grey dotted lines)
districts_study = districts_gdf[districts_gdf.intersects(study_box)]
districts_study.boundary.plot(ax=ax_main, color='#666666', linewidth=0.55, linestyle=':', alpha=0.50, zorder=3)

# Highlight collection districts
thanjavur_dist = districts_gdf[(districts_gdf['district'] == 'Thanjavur') & (districts_gdf['st_nm'] == 'Tamil Nadu')]
palakkad_dist = districts_gdf[(districts_gdf['district'] == 'Palakkad') & (districts_gdf['st_nm'] == 'Kerala')]

thanjavur_dist.boundary.plot(ax=ax_main, color='#b30000', linewidth=1.2, linestyle='--', alpha=0.85, zorder=4)
palakkad_dist.boundary.plot(ax=ax_main, color='#0044cc', linewidth=1.2, linestyle='--', alpha=0.85, zorder=4)

# 4. Render State Boundaries (bold dark line)
states_study = states_gdf[states_gdf.intersects(study_box)]
states_study.boundary.plot(ax=ax_main, color='#222222', linewidth=1.4, linestyle='-', zorder=5)

# 5. Render Rivers (clean azure)
rivers_study = rivers_gdf[rivers_gdf.intersects(study_box)]
rivers_study.plot(ax=ax_main, color='#1f78b4', linewidth=0.9, alpha=0.85, zorder=4)

# 6. Physical and Political Text Labels
# State Names
ax_main.text(78.5, 11.2, "TAMIL NADU", fontsize=13, fontweight='bold', color='#1a1a1a', alpha=0.85, zorder=6, ha='center')
ax_main.text(76.3, 9.8, "KERALA", fontsize=12, fontweight='bold', color='#1a1a1a', alpha=0.85, zorder=6, ha='center', rotation=70)
ax_main.text(76.5, 13.2, "KARNATAKA", fontsize=12, fontweight='bold', color='#1a1a1a', alpha=0.85, zorder=6, ha='center')
ax_main.text(79.3, 13.6, "ANDHRA PRADESH", fontsize=11, fontweight='bold', color='#1a1a1a', alpha=0.85, zorder=6, ha='center')

# Sri Lanka text label
ax_main.text(80.5, 8.8, "SRI LANKA", fontsize=10, fontweight='bold', color='#444444', fontstyle='italic', zorder=6)

# Water bodies (now pristine and open across the Arabian Sea!)
ax_main.text(75.2, 9.5, "ARABIAN SEA", fontsize=13, fontweight='bold', color='#3b6989', fontstyle='italic', zorder=6)
ax_main.text(79.7, 12.3, "BAY OF BENGAL", fontsize=12, fontweight='bold', color='#3b6989', fontstyle='italic', zorder=6)
ax_main.text(79.5, 9.3, "Palk Strait", fontsize=9, color='#3b6989', fontstyle='italic', zorder=6)
ax_main.text(78.6, 8.6, "Gulf of\nMannar", fontsize=9, color='#3b6989', fontstyle='italic', zorder=6, ha='center')
ax_main.text(77.5, 8.1, "INDIAN OCEAN", fontsize=10, fontweight='bold', color='#3b6989', fontstyle='italic', zorder=6, ha='center')

# Mountain ranges and physiographic landmarks
ax_main.text(75.3, 11.8, "WESTERN GHATS", fontsize=10, fontweight='bold', color='#5c2e0b', fontstyle='italic', rotation=-45, zorder=6)
ax_main.text(76.8, 11.5, "Nilgiri Hills", fontsize=8.5, color='#421e05', fontstyle='italic', zorder=6)
ax_main.text(76.9, 10.3, "Anamalai Hills", fontsize=8.5, color='#421e05', fontstyle='italic', zorder=6)
ax_main.text(76.9, 10.75, "Palakkad Gap", fontsize=8, color='#003366', fontweight='bold', zorder=6)
ax_main.text(78.5, 10.9, "Cauvery River", fontsize=8, color='#08519c', fontstyle='italic', zorder=6)

# 7. Collection Localities
# Locality 1: Thanjavur (10.7870°N, 79.1378°E)
ax_main.scatter([loc1_lon], [loc1_lat], s=260, marker='*', facecolor='#d7191c', edgecolor='black', linewidth=1.5, zorder=10)
ax_main.scatter([loc1_lon], [loc1_lat], s=90, marker='*', facecolor='yellow', edgecolor='none', zorder=11)

# Locality 2: Palakkad / Attappadi (11.0679°N, 76.5603°E)
ax_main.scatter([loc2_lon], [loc2_lat], s=200, marker='^', facecolor='#0055ff', edgecolor='black', linewidth=1.5, zorder=10)
ax_main.scatter([loc2_lon], [loc2_lat], s=70, marker='^', facecolor='#00ffff', edgecolor='none', zorder=11)

# 8. Callout Annotation Boxes with Leader Lines
callout1_text = (
    r"$\mathbf{Locality\ 1:\ Thanjavur}$" + "\n"
    r"10.7870°N, 79.1378°E" + "\n"
    r"(10°47'13.2''N, 79°08'16.1''E)" + "\n"
    r"Alt: 59 m a.s.l. | Tamil Nadu"
)
ax_main.annotate(
    callout1_text,
    xy=(loc1_lon, loc1_lat),
    xytext=(loc1_lon + 0.35, loc1_lat - 0.70),
    fontsize=8.5,
    fontfamily='sans-serif',
    bbox=dict(boxstyle="round,pad=0.5", facecolor='#ffffff', edgecolor='#b30000', linewidth=1.4, alpha=0.96),
    arrowprops=dict(arrowstyle="->,head_width=0.4,head_length=0.6", color='#b30000', linewidth=1.4, connectionstyle="arc3,rad=-0.15"),
    zorder=15
)

callout2_text = (
    r"$\mathbf{Locality\ 2:\ Attappadi\ /\ Palakkad}$" + "\n"
    r"11°04'04.5''N, 76°33'36.9''E" + "\n"
    r"(11.0679°N, 76.5603°E)" + "\n"
    r"Alt: 572 m a.s.l. | Kerala (Western Ghats)"
)
ax_main.annotate(
    callout2_text,
    xy=(loc2_lon, loc2_lat),
    xytext=(loc2_lon - 1.85, loc2_lat + 0.65),
    fontsize=8.5,
    fontfamily='sans-serif',
    bbox=dict(boxstyle="round,pad=0.5", facecolor='#ffffff', edgecolor='#0044cc', linewidth=1.4, alpha=0.96),
    arrowprops=dict(arrowstyle="->,head_width=0.4,head_length=0.6", color='#0044cc', linewidth=1.4, connectionstyle="arc3,rad=0.15"),
    zorder=15
)

# 9. Professional Scale Bar (0 to 150 km)
sb_x0, sb_y0 = 74.80, 8.25
km50_deg = 50.0 / 110.1
h_bar = 0.04

ax_main.add_patch(Rectangle((sb_x0, sb_y0), km50_deg, h_bar, facecolor='black', edgecolor='black', linewidth=0.8, zorder=12))
ax_main.add_patch(Rectangle((sb_x0 + km50_deg, sb_y0), km50_deg, h_bar, facecolor='white', edgecolor='black', linewidth=0.8, zorder=12))
ax_main.add_patch(Rectangle((sb_x0 + 2*km50_deg, sb_y0), km50_deg, h_bar, facecolor='black', edgecolor='black', linewidth=0.8, zorder=12))

ax_main.text(sb_x0, sb_y0 + 0.06, "0", fontsize=8, ha='center', fontweight='bold', zorder=12)
ax_main.text(sb_x0 + km50_deg, sb_y0 + 0.06, "50", fontsize=8, ha='center', fontweight='bold', zorder=12)
ax_main.text(sb_x0 + 2*km50_deg, sb_y0 + 0.06, "100", fontsize=8, ha='center', fontweight='bold', zorder=12)
ax_main.text(sb_x0 + 3*km50_deg, sb_y0 + 0.06, "150 km", fontsize=8, ha='center', fontweight='bold', zorder=12)

sb_bg = FancyBboxPatch((sb_x0 - 0.15, sb_y0 - 0.10), 3*km50_deg + 0.45, 0.28,
                       boxstyle="round,pad=0.04", facecolor='white', edgecolor='#666666', linewidth=0.8, alpha=0.92, zorder=11)
ax_main.add_patch(sb_bg)

# 10. True North Arrow (Compass Needle)
nx, ny = 74.85, 13.65
ax_main.annotate('N', xy=(nx, ny + 0.28), xytext=(nx, ny + 0.28),
                 fontsize=12, fontweight='bold', ha='center', va='center', zorder=15)
arrow_l = [(nx, ny + 0.22), (nx - 0.08, ny), (nx, ny - 0.05)]
arrow_r = [(nx, ny + 0.22), (nx + 0.08, ny), (nx, ny - 0.05)]
ax_main.add_patch(MplPolygon(arrow_l, facecolor='black', edgecolor='black', linewidth=1.0, zorder=14))
ax_main.add_patch(MplPolygon(arrow_r, facecolor='white', edgecolor='black', linewidth=1.0, zorder=14))
na_bg = FancyBboxPatch((nx - 0.20, ny - 0.10), 0.40, 0.48,
                       boxstyle="round,pad=0.03", facecolor='white', edgecolor='#666666', linewidth=0.8, alpha=0.92, zorder=13)
ax_main.add_patch(na_bg)

# 11. Hypsometric Elevation Legend
cax_bg = FancyBboxPatch((78.95, 8.15), 1.70, 0.70,
                        boxstyle="round,pad=0.04", facecolor='white', edgecolor='#666666', linewidth=0.8, alpha=0.92, zorder=11)
ax_main.add_patch(cax_bg)
ax_main.text(79.80, 8.70, "Elevation (m a.s.l.)", fontsize=8.5, fontweight='bold', ha='center', zorder=13)

cb_x0, cb_y0 = 79.15, 8.42
cb_w, cb_h = 1.30, 0.08
grad = np.linspace(0, 1, 256).reshape(1, -1)
ax_main.imshow(grad, cmap=cmap_hyp, extent=[cb_x0, cb_x0 + cb_w, cb_y0, cb_y0 + cb_h], zorder=12)
ax_main.add_patch(Rectangle((cb_x0, cb_y0), cb_w, cb_h, facecolor='none', edgecolor='black', linewidth=0.8, zorder=13))

elev_ticks = [(0, "0"), (500, "500"), (1000, "1000"), (1800, "1800"), (2600, "2600m")]
for elev_val, lbl in elev_ticks:
    tx = cb_x0 + (elev_val / 2600.0) * cb_w
    ax_main.plot([tx, tx], [cb_y0, cb_y0 - 0.025], color='black', linewidth=0.8, zorder=13)
    ax_main.text(tx, cb_y0 - 0.07, lbl, fontsize=7, ha='center', zorder=13)

# Main Axis Limits and Coordinate Graticules
ax_main.set_xlim(lon_min, lon_max)
ax_main.set_ylim(lat_min, lat_max)
ax_main.set_aspect('equal')

ax_main.set_xticks(np.arange(75.0, 81.0, 1.0))
ax_main.set_yticks(np.arange(8.0, 15.0, 1.0))
ax_main.set_xticklabels([f"{int(x)}°E" for x in np.arange(75.0, 81.0, 1.0)], fontsize=9, fontweight='bold')
ax_main.set_yticklabels([f"{int(y)}°N" for y in np.arange(8.0, 15.0, 1.0)], fontsize=9, fontweight='bold')
ax_main.grid(True, linestyle='--', linewidth=0.5, color='#999999', alpha=0.40, zorder=7)

for spine in ax_main.spines.values():
    spine.set_edgecolor('black')
    spine.set_linewidth(1.3)

# -------------------------------------------------------------
# 12. INSET PANEL: SURVEY OF INDIA NATIONAL MAP (SMOOTH & POLISHED)
# -------------------------------------------------------------
# Position: Upper-right corner
ax_inset = fig.add_axes([0.62, 0.62, 0.32, 0.30])
ax_inset.set_facecolor('#dbeaf8')

in_lon_min, in_lon_max = 67.5, 98.0
in_lat_min, in_lat_max = 6.0, 37.5
inset_box = box(in_lon_min, in_lat_min, in_lon_max, in_lat_max)

# 10m high-resolution land for all South Asia in inset
land_10m_inset = land_10m_gdf[land_10m_gdf.intersects(inset_box)].clip(inset_box)

# Render relief raster across the inset
im_in_raster = ax_inset.imshow(
    raster_india,
    extent=[meta_india['lon_left'], meta_india['lon_right'], meta_india['lat_bottom'], meta_india['lat_top']],
    origin='upper',
    interpolation='bicubic',
    zorder=1
)

# Smooth vector clipping for the inset land
all_land_inset_geom = land_10m_inset.geometry.union_all().union(india_highres_gdf.geometry.union_all())
all_land_inset_path = shapely_to_mpl_path(all_land_inset_geom)
if all_land_inset_path:
    clip_patch_in = PathPatch(all_land_inset_path, facecolor='none', edgecolor='none', transform=ax_inset.transData)
    ax_inset.add_patch(clip_patch_in)
    im_in_raster.set_clip_path(clip_patch_in)

# Render neighboring countries with soft neutral fill and dashed border
ne_neighbors = ne_countries[ne_countries['SOVEREIGNT'] != 'India'].clip(inset_box)
ne_neighbors.plot(ax=ax_inset, facecolor='#eae6df', edgecolor='#777777', linewidth=0.4, linestyle='--', zorder=2)

# Sri Lanka smooth 10m in inset
sl_inset = land_10m_gdf[land_10m_gdf.intersects(box(79.0, 5.8, 82.5, 10.0))].clip(inset_box)
sl_inset.boundary.plot(ax=ax_inset, color='#444444', linewidth=0.7, zorder=5)

# Render Official Survey of India State Boundaries inside India
states_gdf.plot(ax=ax_inset, facecolor='none', edgecolor='#666666', linewidth=0.35, zorder=4)

# Official Survey of India Outer Boundary (252,604 vertices - silky smooth!)
india_highres_gdf.boundary.plot(ax=ax_inset, color='#000000', linewidth=1.2, zorder=6)

# Labels for neighboring countries
ax_inset.text(70.0, 30.0, "PAKISTAN", fontsize=6, color='#555555', ha='center', zorder=7)
ax_inset.text(85.0, 32.5, "CHINA / TIBET", fontsize=6, color='#555555', ha='center', zorder=7)
ax_inset.text(83.0, 28.2, "NEPAL", fontsize=5.5, color='#555555', ha='center', zorder=7)
ax_inset.text(90.5, 27.5, "BHU", fontsize=5, color='#555555', ha='center', zorder=7)
ax_inset.text(90.0, 24.0, "BANGLADESH", fontsize=5.5, color='#555555', ha='center', zorder=7)
ax_inset.text(95.5, 22.0, "MYANMAR", fontsize=5.5, color='#555555', ha='center', zorder=7)
ax_inset.text(81.0, 7.5, "SRI LANKA", fontsize=5.5, color='#555555', ha='center', zorder=7)

# Territory labels emphasizing SOI compliance
ax_inset.text(77.0, 35.0, "LADAKH", fontsize=5.5, fontweight='bold', color='#222222', ha='center', zorder=7)
ax_inset.text(74.5, 33.5, "J&K", fontsize=5, fontweight='bold', color='#222222', ha='center', zorder=7)
ax_inset.text(94.5, 28.2, "ARUNACHAL\nPRADESH", fontsize=4.5, fontweight='bold', color='#222222', ha='center', zorder=7)

# Red Study Area Bounding Box on National Inset
study_rect = Rectangle((lon_min, lat_min), lon_max - lon_min, lat_max - lat_min,
                       facecolor='#ff0000', edgecolor='#cc0000', linewidth=1.5, alpha=0.25, zorder=8)
ax_inset.add_patch(study_rect)
study_rect_edge = Rectangle((lon_min, lat_min), lon_max - lon_min, lat_max - lat_min,
                            facecolor='none', edgecolor='#b30000', linewidth=1.5, linestyle='-', zorder=9)
ax_inset.add_patch(study_rect_edge)

# Mark the two points on the national inset
ax_inset.scatter([loc1_lon], [loc1_lat], s=25, marker='*', facecolor='#d7191c', edgecolor='black', linewidth=0.5, zorder=10)
ax_inset.scatter([loc2_lon], [loc2_lat], s=18, marker='^', facecolor='#0055ff', edgecolor='black', linewidth=0.5, zorder=10)

# Inset title banner
ax_inset.text(82.5, 36.8, "INDIA\n(Survey of India Boundary)", fontsize=7, fontweight='bold', color='#000000',
              ha='center', va='top', bbox=dict(boxstyle='round,pad=0.2', facecolor='white', edgecolor='#444444', linewidth=0.6, alpha=0.92), zorder=11)

ax_inset.set_xlim(in_lon_min, in_lon_max)
ax_inset.set_ylim(in_lat_min, in_lat_max)
ax_inset.set_aspect('equal')

ax_inset.set_xticks([70, 80, 90])
ax_inset.set_yticks([10, 20, 30])
ax_inset.set_xticklabels(['70°E', '80°E', '90°E'], fontsize=6)
ax_inset.set_yticklabels(['10°N', '20°N', '30°N'], fontsize=6)
ax_inset.tick_params(axis='both', which='both', length=2.5, pad=1.5)

for spine in ax_inset.spines.values():
    spine.set_edgecolor('#222222')
    spine.set_linewidth(1.1)

# Notice: (A) and (B) and MAP LEGEND have been completely removed as requested!

# Main Title and Subtitle at top
fig.text(0.50, 0.975, "Geographic Distribution of Study Localities",
         fontsize=14, fontweight='bold', ha='center', va='top')
fig.text(0.50, 0.953, "Peninsular India Topographic Relief Map with Survey of India Administrative Boundaries",
         fontsize=10, fontstyle='italic', ha='center', va='top', color='#333333')

# Footer / Compliance attribution
fig.text(0.08, 0.035,
         "Data sources: Topographic Digital Elevation Model (SRTM/GMTED via Terrarium); Administrative boundaries conforming to official Survey of India (SOI) demarcation; Hydrography via Natural Earth.",
         fontsize=7.5, color='#444444', ha='left')
fig.text(0.08, 0.020,
         "Locality 1: 10.7870°N, 79.1378°E (Thanjavur, Tamil Nadu, 59 m a.s.l.) | Locality 2: 11°04'04.5\"N, 76°33'36.9\"E [11.0679°N, 76.5603°E] (Attappadi / Palakkad, Kerala, 572 m a.s.l.)",
         fontsize=7.5, color='#111111', fontweight='semibold', ha='left')

# Save outputs in multiple formats
png_path = os.path.join(out_dir, "Figure_1_Taxonomy_Map_Composite.png")
svg_path = os.path.join(out_dir, "Figure_1_Taxonomy_Map_Composite.svg")
pdf_path = os.path.join(out_dir, "Figure_1_Taxonomy_Map_Composite.pdf")

print("Saving PNG (300 DPI)...")
fig.savefig(png_path, dpi=300, facecolor='white', bbox_inches='tight')

print("Saving SVG vector format...")
fig.savefig(svg_path, format='svg', facecolor='white', bbox_inches='tight')

print("Saving PDF vector format...")
fig.savefig(pdf_path, format='pdf', facecolor='white', bbox_inches='tight')

plt.close(fig)
print(f"Updated Figure 1 created!\nPNG: {png_path}\nSVG: {svg_path}\nPDF: {pdf_path}")
