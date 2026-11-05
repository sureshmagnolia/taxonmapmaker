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
from shapely.geometry import box, Point
from scipy.ndimage import gaussian_filter, sobel

matplotlib.rcParams.update({
    'font.family': 'sans-serif',
    'font.sans-serif': ['Arial', 'DejaVu Sans', 'Liberation Sans'],
    'font.size': 10,
    'axes.labelsize': 10,
    'xtick.labelsize': 8.5,
    'ytick.labelsize': 8.5,
    'pdf.fonttype': 42,
    'svg.fonttype': 'none',
    'figure.dpi': 300,
    'savefig.dpi': 300,
})

data_dir = r"C:\Users\sures\.gemini\antigravity\scratch\india_taxonomy_map\data"
out_dir = r"C:\Users\sures\.gemini\antigravity\scratch\india_taxonomy_map\figures"
os.makedirs(out_dir, exist_ok=True)

print("Loading data for Figure 2 (All-India Master Map)...")
india_highres_gdf = gpd.read_file(os.path.join(data_dir, "india-composite.geojson"))
states_gdf = gpd.read_file(os.path.join(data_dir, "india_states_smooth.geojson"))
districts_gdf = gpd.read_file(os.path.join(data_dir, "india_districts_smooth.geojson"))
land_10m_gdf = gpd.read_file(os.path.join(data_dir, "sri_lanka_smooth.geojson"))
ne_countries = gpd.read_file(os.path.join(data_dir, "ne_110m_countries.geojson"))
rivers_gdf = gpd.read_file(os.path.join(data_dir, "rivers_india_smooth.geojson"))

raster_india = np.load(os.path.join(data_dir, "raster_india_all.npy"))
with open(os.path.join(data_dir, "dem_india_all_meta.json"), "r") as f:
    meta_india = json.load(f)

# Locations
loc1_lon, loc1_lat = 79.1378, 10.7870
loc2_lon, loc2_lat = 76.56025, 11.067917

in_lon_min, in_lon_max = 67.5, 98.2
in_lat_min, in_lat_max = 6.2, 37.6
all_box = box(in_lon_min, in_lat_min, in_lon_max, in_lat_max)

fig = plt.figure(figsize=(11.5, 12.0), facecolor='white')
ax_main = fig.add_axes([0.08, 0.08, 0.88, 0.86])
ax_main.set_facecolor('#dbeaf8')

# 1. Render all-India topographic relief raster
ax_main.imshow(raster_india, extent=[meta_india['lon_left'], meta_india['lon_right'], meta_india['lat_bottom'], meta_india['lat_top']],
               origin='upper', interpolation='bicubic', zorder=1)

# 2. Render neighboring countries
ne_neighbors = ne_countries[ne_countries['SOVEREIGNT'] != 'India'].clip(all_box)
ne_neighbors.plot(ax=ax_main, facecolor='#eae6df', edgecolor='#777777', linewidth=0.5, linestyle='--', zorder=2)

# Sri Lanka smooth land in main map
sl_all = land_10m_gdf.clip(all_box)
sl_all.boundary.plot(ax=ax_main, color='#444444', linewidth=0.8, zorder=5)

# 3. Render Major Rivers
rivers_gdf.clip(all_box).plot(ax=ax_main, color='#1f78b4', linewidth=0.75, alpha=0.8, zorder=3)

# 4. Render Official Survey of India State Boundaries
states_gdf.boundary.plot(ax=ax_main, color='#444444', linewidth=0.6, linestyle='-', zorder=4)

# 5. Render Official Survey of India National Outer Boundary (252k vertices - silky smooth!)
india_highres_gdf.boundary.plot(ax=ax_main, color='#000000', linewidth=1.4, zorder=6)

# 6. Physical and Country Labels
ax_main.text(70.0, 29.5, "PAKISTAN", fontsize=9, color='#555555', fontstyle='italic', ha='center', zorder=7)
ax_main.text(85.0, 33.0, "CHINA / TIBET", fontsize=10, color='#555555', fontstyle='italic', ha='center', zorder=7)
ax_main.text(84.0, 28.5, "NEPAL", fontsize=8.5, color='#555555', fontstyle='italic', ha='center', zorder=7)
ax_main.text(90.5, 27.5, "BHUTAN", fontsize=7.5, color='#555555', fontstyle='italic', ha='center', zorder=7)
ax_main.text(90.2, 23.8, "BANGLADESH", fontsize=8.5, color='#555555', fontstyle='italic', ha='center', zorder=7)
ax_main.text(96.0, 21.5, "MYANMAR", fontsize=8.5, color='#555555', fontstyle='italic', ha='center', zorder=7)
ax_main.text(81.0, 7.8, "SRI LANKA", fontsize=8.5, color='#555555', fontstyle='italic', ha='center', zorder=7)

# Ocean Labels
ax_main.text(69.5, 16.0, "ARABIAN SEA", fontsize=12, fontweight='bold', color='#3b6989', fontstyle='italic', zorder=7)
ax_main.text(88.5, 15.0, "BAY OF BENGAL", fontsize=12, fontweight='bold', color='#3b6989', fontstyle='italic', zorder=7)
ax_main.text(78.5, 6.5, "INDIAN OCEAN", fontsize=11, fontweight='bold', color='#3b6989', fontstyle='italic', zorder=7, ha='center')

# Territory Labels (SOI compliance)
ax_main.text(77.2, 34.8, "LADAKH (UT)", fontsize=8, fontweight='bold', color='#222222', ha='center', zorder=7)
ax_main.text(74.5, 33.5, "JAMMU &\nKASHMIR", fontsize=7, fontweight='bold', color='#222222', ha='center', zorder=7)
ax_main.text(94.2, 28.2, "ARUNACHAL\nPRADESH", fontsize=7.5, fontweight='bold', color='#222222', ha='center', zorder=7)
ax_main.text(93.0, 12.0, "ANDAMAN & NICOBAR\nISLANDS", fontsize=7, fontweight='bold', color='#222222', ha='center', zorder=7)
ax_main.text(72.2, 10.5, "LAKSHADWEEP", fontsize=6.5, fontweight='bold', color='#222222', ha='center', zorder=7)

# 7. Collection Localities on Main Map
ax_main.scatter([loc1_lon], [loc1_lat], s=200, marker='*', facecolor='#d7191c', edgecolor='black', linewidth=1.2, zorder=10)
ax_main.scatter([loc2_lon], [loc2_lat], s=140, marker='^', facecolor='#0055ff', edgecolor='black', linewidth=1.2, zorder=10)

sub_lon_min, sub_lon_max = 75.5, 80.2
sub_lat_min, sub_lat_max = 9.8, 12.2
rect_study = Rectangle((sub_lon_min, sub_lat_min), sub_lon_max - sub_lon_min, sub_lat_max - sub_lat_min,
                       facecolor='none', edgecolor='#b30000', linewidth=1.8, linestyle='-', zorder=9)
ax_main.add_patch(rect_study)

# 8. REGIONAL INSET PANEL (Magnified Southern India Collection Area)
ax_inset = fig.add_axes([0.10, 0.48, 0.38, 0.40])
ax_inset.set_facecolor('#dbeaf8')

dem_south = np.load(os.path.join(data_dir, "dem_south_india.npy"))
with open(os.path.join(data_dir, "dem_south_india_meta.json"), "r") as f: meta_south = json.load(f)

in_lon1, in_lon2 = 75.2, 80.2
in_lat1, in_lat2 = 9.8, 12.2
inset_sub_box = box(in_lon1, in_lat1, in_lon2, in_lat2)

h_s, w_s = dem_south.shape
px_1 = int((in_lon1 - meta_south['lon_left']) / (meta_south['lon_right'] - meta_south['lon_left']) * w_s)
px_2 = int((in_lon2 - meta_south['lon_left']) / (meta_south['lon_right'] - meta_south['lon_left']) * w_s)
py_1 = int((meta_south['lat_top'] - in_lat2) / (meta_south['lat_top'] - meta_south['lat_bottom']) * h_s)
py_2 = int((meta_south['lat_top'] - in_lat1) / (meta_south['lat_top'] - meta_south['lat_bottom']) * h_s)

dem_in = dem_south[py_1:py_2, px_1:px_2]
dem_in_s = gaussian_filter(dem_in, sigma=1.0)
deg_lat = in_lat2 - in_lat1
deg_lon = in_lon2 - in_lon1
dy = (deg_lat * 110574.0) / dem_in.shape[0]
dx = (deg_lon * 109280.0) / dem_in.shape[1]
zy = sobel(dem_in_s, axis=0) / (8.0 * dy)
zx = sobel(dem_in_s, axis=1) / (8.0 * dx)
sl = np.arctan(np.sqrt(zx**2 + zy**2))
asp = np.arctan2(-zy, zx)
def chs(s, a, alt, az):
    return np.clip(np.sin(np.radians(alt))*np.cos(s) + np.cos(np.radians(alt))*np.sin(s)*np.cos(np.radians(az) - a), 0, 1)
hs_in = 0.7 * chs(sl, asp, 45, 315) + 0.3 * chs(sl, asp, 35, 225)
hs_in = (hs_in - hs_in.min()) / (hs_in.max() - hs_in.min() + 1e-5)

colors_hyps = [
    (0.00, '#a1d99b'), (0.05, '#c7e9c0'), (0.15, '#edf8b1'), (0.28, '#fed976'),
    (0.45, '#feb24c'), (0.65, '#fd8d3c'), (0.80, '#e6550d'), (0.92, '#a63603'), (1.00, '#4a1400')
]
cmap_in = LinearSegmentedColormap.from_list('in_hyps', [(p, c) for p, c in colors_hyps], N=256)
rgb_in = cmap_in(np.clip(dem_in, 0, 2600) / 2600.0)[:, :, :3]
blended_in = np.clip(rgb_in * (0.40 + 0.60 * hs_in[:, :, np.newaxis]) * 1.15, 0, 1)

# Clip raster in inset to smooth 10m land
india_in_land = india_highres_gdf.clip(inset_sub_box)
def shapely_to_mpl_path(geom):
    if geom is None or geom.is_empty: return None
    polys = [geom] if geom.geom_type == 'Polygon' else list(geom.geoms) if geom.geom_type == 'MultiPolygon' else []
    verts, codes = [], []
    for poly in polys:
        ext = np.asarray(poly.exterior.coords)
        if len(ext) < 3: continue
        verts.extend(ext)
        codes.append(Path.MOVETO)
        codes.extend([Path.LINETO] * (len(ext) - 2))
        codes.append(Path.CLOSEPOLY)
    return Path(verts, codes) if verts else None

path_in = shapely_to_mpl_path(india_in_land.geometry.union_all())

im_in = ax_inset.imshow(blended_in, extent=[in_lon1, in_lon2, in_lat1, in_lat2], origin='upper', interpolation='bicubic', zorder=2)
if path_in:
    cpatch = PathPatch(path_in, facecolor='none', edgecolor='none', transform=ax_inset.transData)
    ax_inset.add_patch(cpatch)
    im_in.set_clip_path(cpatch)

# Smooth vector boundaries in inset
india_in_land.boundary.plot(ax=ax_inset, color='#262626', linewidth=1.1, zorder=5)

districts_in = districts_gdf[districts_gdf.intersects(inset_sub_box)]
districts_in.boundary.plot(ax=ax_inset, color='#666666', linewidth=0.5, linestyle=':', alpha=0.50, zorder=3)

thanjavur_dist = districts_gdf[(districts_gdf['district'] == 'Thanjavur') & (districts_gdf['st_nm'] == 'Tamil Nadu')]
palakkad_dist = districts_gdf[(districts_gdf['district'] == 'Palakkad') & (districts_gdf['st_nm'] == 'Kerala')]
thanjavur_dist.boundary.plot(ax=ax_inset, color='#b30000', linewidth=1.1, linestyle='--', alpha=0.85, zorder=4)
palakkad_dist.boundary.plot(ax=ax_inset, color='#0044cc', linewidth=1.1, linestyle='--', alpha=0.85, zorder=4)

states_in = states_gdf[states_gdf.intersects(inset_sub_box)]
states_in.boundary.plot(ax=ax_inset, color='#222222', linewidth=1.2, linestyle='-', zorder=5)

rivers_in = rivers_gdf[rivers_gdf.intersects(inset_sub_box)]
rivers_in.plot(ax=ax_inset, color='#1f78b4', linewidth=0.8, zorder=4)

# Markers and Callouts in Inset
ax_inset.scatter([loc1_lon], [loc1_lat], s=180, marker='*', facecolor='#d7191c', edgecolor='black', linewidth=1.2, zorder=10)
ax_inset.scatter([loc1_lon], [loc1_lat], s=60, marker='*', facecolor='yellow', edgecolor='none', zorder=11)

ax_inset.scatter([loc2_lon], [loc2_lat], s=130, marker='^', facecolor='#0055ff', edgecolor='black', linewidth=1.2, zorder=10)
ax_inset.scatter([loc2_lon], [loc2_lat], s=45, marker='^', facecolor='#00ffff', edgecolor='none', zorder=11)

ax_inset.annotate(
    "Locality 1: Thanjavur\n10.7870°N, 79.1378°E (59m)",
    xy=(loc1_lon, loc1_lat), xytext=(loc1_lon - 1.6, loc1_lat - 0.55),
    fontsize=7.5, fontweight='semibold',
    bbox=dict(boxstyle="round,pad=0.3", facecolor='white', edgecolor='#b30000', linewidth=1.1, alpha=0.95),
    arrowprops=dict(arrowstyle="->", color='#b30000', linewidth=1.1),
    zorder=15
)

ax_inset.annotate(
    "Locality 2: Palakkad\n11°04'04.5\"N, 76°33'36.9\"E (572m)",
    xy=(loc2_lon, loc2_lat), xytext=(loc2_lon - 0.2, loc2_lat + 0.60),
    fontsize=7.5, fontweight='semibold',
    bbox=dict(boxstyle="round,pad=0.3", facecolor='white', edgecolor='#0044cc', linewidth=1.1, alpha=0.95),
    arrowprops=dict(arrowstyle="->", color='#0044cc', linewidth=1.1),
    zorder=15
)

ax_inset.text(77.8, 11.2, "TAMIL NADU", fontsize=9, fontweight='bold', color='#222222', alpha=0.8, ha='center', zorder=6)
ax_inset.text(76.2, 10.3, "KERALA", fontsize=8.5, fontweight='bold', color='#222222', alpha=0.8, ha='center', zorder=6)
ax_inset.text(76.8, 11.6, "Nilgiris", fontsize=7.5, color='#421e05', fontstyle='italic', zorder=6)
ax_inset.text(76.9, 10.7, "Palakkad Gap", fontsize=7, color='#003366', fontweight='bold', zorder=6)

ax_inset.set_xlim(in_lon1, in_lon2)
ax_inset.set_ylim(in_lat1, in_lat2)
ax_inset.set_xticks([76.0, 77.0, 78.0, 79.0, 80.0])
ax_inset.set_yticks([10.0, 11.0, 12.0])
ax_inset.set_xticklabels(['76°E', '77°E', '78°E', '79°E', '80°E'], fontsize=7)
ax_inset.set_yticklabels(['10°N', '11°N', '12°N'], fontsize=7)
ax_inset.tick_params(axis='both', which='both', length=2.5, pad=1.5)
ax_inset.grid(True, linestyle=':', linewidth=0.5, color='#999999', alpha=0.4)

for spine in ax_inset.spines.values():
    spine.set_edgecolor('#b30000')
    spine.set_linewidth(1.3)

ax_inset.text(0.03, 0.94, "Detailed Study Region", transform=ax_inset.transAxes, fontsize=8.5, fontweight='bold',
              bbox=dict(boxstyle='round,pad=0.2', facecolor='white', edgecolor='#444444', linewidth=0.5, alpha=0.9), zorder=20)

# 9. Main Axis Frame, Scale Bar, Compass
ax_main.set_xlim(in_lon_min, in_lon_max)
ax_main.set_ylim(in_lat_min, in_lat_max)
ax_main.set_aspect('equal')

ax_main.set_xticks(np.arange(70.0, 100.0, 5.0))
ax_main.set_yticks(np.arange(10.0, 40.0, 5.0))
ax_main.set_xticklabels([f"{int(x)}°E" for x in np.arange(70.0, 100.0, 5.0)], fontsize=8.5, fontweight='bold')
ax_main.set_yticklabels([f"{int(y)}°N" for y in np.arange(10.0, 40.0, 5.0)], fontsize=8.5, fontweight='bold')
ax_main.grid(True, linestyle='--', linewidth=0.5, color='#999999', alpha=0.35, zorder=6)

for spine in ax_main.spines.values():
    spine.set_edgecolor('black')
    spine.set_linewidth(1.3)

# Scale bar
sb_x0, sb_y0 = 69.5, 8.5
km250_deg = 250.0 / 104.6
h_b = 0.25
ax_main.add_patch(Rectangle((sb_x0, sb_y0), km250_deg, h_b, facecolor='black', edgecolor='black', linewidth=0.8, zorder=12))
ax_main.add_patch(Rectangle((sb_x0 + km250_deg, sb_y0), km250_deg, h_b, facecolor='white', edgecolor='black', linewidth=0.8, zorder=12))
ax_main.text(sb_x0, sb_y0 + 0.35, "0", fontsize=7.5, ha='center', fontweight='bold', zorder=12)
ax_main.text(sb_x0 + km250_deg, sb_y0 + 0.35, "250", fontsize=7.5, ha='center', fontweight='bold', zorder=12)
ax_main.text(sb_x0 + 2*km250_deg, sb_y0 + 0.35, "500 km", fontsize=7.5, ha='center', fontweight='bold', zorder=12)

sb_bg = FancyBboxPatch((sb_x0 - 0.8, sb_y0 - 0.5), 2*km250_deg + 1.8, 1.4,
                       boxstyle="round,pad=0.1", facecolor='white', edgecolor='#666666', linewidth=0.8, alpha=0.92, zorder=11)
ax_main.add_patch(sb_bg)

# North Arrow
nx, ny = 94.5, 33.5
ax_main.annotate('N', xy=(nx, ny + 1.4), fontsize=11, fontweight='bold', ha='center', va='center', zorder=15)
ax_main.add_patch(MplPolygon([(nx, ny + 1.1), (nx - 0.4, ny), (nx, ny - 0.3)], facecolor='black', edgecolor='black', linewidth=0.8, zorder=14))
ax_main.add_patch(MplPolygon([(nx, ny + 1.1), (nx + 0.4, ny), (nx, ny - 0.3)], facecolor='white', edgecolor='black', linewidth=0.8, zorder=14))
na_bg = FancyBboxPatch((nx - 0.9, ny - 0.6), 1.8, 2.4, boxstyle="round,pad=0.1", facecolor='white', edgecolor='#666666', linewidth=0.8, alpha=0.92, zorder=13)
ax_main.add_patch(na_bg)

# Elevation legend
cax_bg = FancyBboxPatch((69.0, 11.0), 6.5, 2.2, boxstyle="round,pad=0.1", facecolor='white', edgecolor='#666666', linewidth=0.8, alpha=0.92, zorder=11)
ax_main.add_patch(cax_bg)
ax_main.text(72.25, 12.6, "Elevation (m a.s.l.)", fontsize=8, fontweight='bold', ha='center', zorder=13)
cb_x0, cb_y0 = 69.5, 11.8
cb_w, cb_h = 5.5, 0.35
grad = np.linspace(0, 1, 256).reshape(1, -1)
colors_hyps_all = [
    (0.00, '#a1d99b'), (0.05, '#c7e9c0'), (0.12, '#edf8b1'), (0.25, '#fed976'),
    (0.40, '#feb24c'), (0.55, '#fd8d3c'), (0.70, '#e6550d'), (0.85, '#a63603'), (1.00, '#f7f4f9')
]
cmap_all = LinearSegmentedColormap.from_list('india_hyps', [(p, c) for p, c in colors_hyps_all], N=256)
ax_main.imshow(grad, cmap=cmap_all, extent=[cb_x0, cb_x0 + cb_w, cb_y0, cb_y0 + cb_h], zorder=12)
ax_main.add_patch(Rectangle((cb_x0, cb_y0), cb_w, cb_h, facecolor='none', edgecolor='black', linewidth=0.6, zorder=13))
for val, lbl in [(0, "0"), (1000, "1000"), (2500, "2500"), (4500, "4500"), (7000, "7000m")]:
    tx = cb_x0 + (val / 7000.0) * cb_w
    ax_main.plot([tx, tx], [cb_y0, cb_y0 - 0.08], color='black', linewidth=0.6, zorder=13)
    ax_main.text(tx, cb_y0 - 0.28, lbl, fontsize=6.5, ha='center', zorder=13)

fig.text(0.50, 0.975, "National Distribution of Study Taxa Across India",
         fontsize=14, fontweight='bold', ha='center', va='top')
fig.text(0.50, 0.953, "Full Country Relief Map with Survey of India Borders and Southern India Study Inset",
         fontsize=10, fontstyle='italic', ha='center', va='top', color='#333333')

fig.text(0.08, 0.035,
         "Administrative boundaries: Official Survey of India (SOI) delineation, Government of India. Topography: SRTM / GMTED. Projection: Geographic (WGS84).",
         fontsize=7.5, color='#444444', ha='left')
fig.text(0.08, 0.020,
         "Localities: [1] 10.7870°N, 79.1378°E (Thanjavur, TN, 59m); [2] 11°04'04.5\"N, 76°33'36.9\"E [11.0679°N, 76.5603°E] (Palakkad, KL, 572m).",
         fontsize=7.5, color='#111111', fontweight='semibold', ha='left')

png2 = os.path.join(out_dir, "Figure_2_All_India_Taxonomy_Map.png")
svg2 = os.path.join(out_dir, "Figure_2_All_India_Taxonomy_Map.svg")
pdf2 = os.path.join(out_dir, "Figure_2_All_India_Taxonomy_Map.pdf")

print("Saving Figure 2 PNG (300 DPI)...")
fig.savefig(png2, dpi=300, facecolor='white', bbox_inches='tight')
print("Saving Figure 2 SVG...")
fig.savefig(svg2, format='svg', facecolor='white', bbox_inches='tight')
print("Saving Figure 2 PDF...")
fig.savefig(pdf2, format='pdf', facecolor='white', bbox_inches='tight')

plt.close(fig)
print("Figure 2 successfully generated!")
