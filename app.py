import os
import io
import math
import json
import numpy as np
import streamlit as st
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
import folium

# Page configuration
st.set_page_config(
    page_title="TaxonMap Pro - Taxonomy Map Studio",
    page_icon="🌿",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Paths
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")
OUT_DIR = os.path.join(BASE_DIR, "figures")
os.makedirs(OUT_DIR, exist_ok=True)

# Helper function to convert DMS to Decimal Degrees
def dms_to_dd(dms_str):
    dms_str = dms_str.strip()
    try:
        # Check if already decimal
        return float(dms_str)
    except ValueError:
        pass
    
    import re
    # Parse e.g. 11°04'04.5"N or 76°33'36.9"E
    match = re.search(r"(\d+)[°\s]+(\d+)['\s]+([\d.]+)?[\"\s]*([NSEWnsew])?", dms_str)
    if match:
        deg = float(match.group(1))
        minute = float(match.group(2))
        sec = float(match.group(3)) if match.group(3) else 0.0
        direction = match.group(4).upper() if match.group(4) else 'N'
        dd = deg + minute / 60.0 + sec / 3600.0
        if direction in ['S', 'W']:
            dd = -dd
        return dd
    raise ValueError(f"Could not parse coordinate: {dms_str}")

def dd_to_dms(dd, is_lat=True):
    abs_dd = abs(dd)
    deg = int(abs_dd)
    min_float = (abs_dd - deg) * 60.0
    minute = int(min_float)
    sec = (min_float - minute) * 60.0
    if is_lat:
        direction = "N" if dd >= 0 else "S"
    else:
        direction = "E" if dd >= 0 else "W"
    return f"{deg:02d}°{minute:02d}'{sec:04.1f}\"{direction}"

# Cache static datasets
@st.cache_resource
def load_spatial_data():
    india_highres = gpd.read_file(os.path.join(DATA_DIR, "india-composite.geojson"))
    states = gpd.read_file(os.path.join(DATA_DIR, "india_states_smooth.geojson"))
    districts = gpd.read_file(os.path.join(DATA_DIR, "india_districts_smooth.geojson"))
    land_10m = gpd.read_file(os.path.join(DATA_DIR, "sri_lanka_smooth.geojson"))
    rivers = gpd.read_file(os.path.join(DATA_DIR, "rivers_india_smooth.geojson"))
    ne_countries = gpd.read_file(os.path.join(DATA_DIR, "ne_110m_countries.geojson"))
    
    dem_south = np.load(os.path.join(DATA_DIR, "dem_south_india.npy"))
    with open(os.path.join(DATA_DIR, "dem_south_india_meta.json"), "r") as f:
        meta_south = json.load(f)
        
    raster_india = np.load(os.path.join(DATA_DIR, "raster_india_all.npy"))
    with open(os.path.join(DATA_DIR, "dem_india_all_meta.json"), "r") as f:
        meta_india = json.load(f)
        
    return india_highres, states, districts, land_10m, rivers, ne_countries, dem_south, meta_south, raster_india, meta_india

india_highres, states_gdf, districts_gdf, land_10m, rivers_gdf, ne_countries, dem_south, meta_south, raster_india, meta_india = load_spatial_data()

# Helper: Convert Shapely to Matplotlib Path
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
        for interior in poly.interiors:
            inte = np.asarray(interior.coords)
            if len(inte) < 3: continue
            verts.extend(inte)
            codes.append(Path.MOVETO)
            codes.extend([Path.LINETO] * (len(inte) - 2))
            codes.append(Path.CLOSEPOLY)
    return Path(verts, codes) if verts else None

# Session state initialization for plants and specimens
if 'taxa' not in st.session_state:
    st.session_state.taxa = [
        {
            'name': 'Study Taxon A',
            'symbol': '*',
            'color': '#D7191C',
            'specimens': [
                {
                    'label': 'Locality 1: Thanjavur',
                    'lat_str': '10.7870',
                    'lon_str': '79.1378',
                    'status': 'Holotype',
                    'alt_m': 59
                }
            ]
        },
        {
            'name': 'Study Taxon B',
            'symbol': '^',
            'color': '#0055FF',
            'specimens': [
                {
                    'label': 'Locality 2: Attappadi / Palakkad',
                    'lat_str': '11°04\'04.5"N',
                    'lon_str': '76°33\'36.9"E',
                    'status': 'Paratype',
                    'alt_m': 572
                }
            ]
        }
    ]

# -------------------------------------------------------------
# APPLICATION HEADER
# -------------------------------------------------------------
st.title("🌿 TaxonMap Pro")
st.markdown("**Camera-Ready Taxonomy Map Studio for Indian Flora & Fauna** | 100% Survey of India (SOI) Compliant")

# -------------------------------------------------------------
# SIDEBAR CONTROLS
# -------------------------------------------------------------
with st.sidebar:
    st.header("⚙️ Map Settings & Layers")
    
    # 1. Color Theme Selection
    st.subheader("🎨 Elevation Color Theme")
    theme_choice = st.selectbox(
        "Select Cartographic Palette",
        [
            "Phytotaxa Standard (Verdant to Montane Umber)",
            "Nordic Monochromatic (Grayscale for Print)",
            "Swiss Alpine Shaded Relief",
            "Coromandel & Deccan Warm Earth",
            "Clean Minimalist (Vector Contours)"
        ]
    )
    
    # 2. Layer Toggles
    st.subheader("🗺️ Layer Toggles")
    show_rivers = st.checkbox("Water Bodies & River Networks", value=True)
    show_sl = st.checkbox("Smooth Sri Lanka Coastline (10m)", value=True)
    show_districts = st.checkbox("District Boundaries (Dotted)", value=True)
    highlight_districts = st.checkbox("Highlight Collection Districts", value=True)
    show_mountains = st.checkbox("Mountain Ranges (Western Ghats, etc.)", value=True)
    show_places = st.checkbox("Major State & Water Labels", value=True)
    
    # 3. Scientific Accoutrements
    st.subheader("📐 Map Elements")
    show_scalebar = st.checkbox("Scale Bar (0–150 km)", value=True)
    show_compass = st.checkbox("True North Compass Needle", value=True)
    show_elev_bar = st.checkbox("Hypsometric Elevation Colorbar", value=True)
    show_legend = st.checkbox("Map Legend Box (Off by Default)", value=False)
    
    # 4. National Inset Map of India
    st.subheader("🇮🇳 National Inset of India")
    show_inset = st.checkbox("Display Survey of India Inset Map", value=True)
    inset_pos = st.selectbox("Inset Position", ["Top-Right", "Top-Left", "Bottom-Right", "Bottom-Left"], index=0)

# -------------------------------------------------------------
# MAIN CONTENT AREA
# -------------------------------------------------------------
tab_data, tab_preview, tab_interactive = st.tabs(["📋 1. Taxa & Coordinate Input", "🗺️ 2. Publication Figure Preview", "📍 3. Interactive Waypoint Pin Dropper"])

with tab_data:
    st.subheader("Add and Manage Study Taxa & Collection Localities")
    
    col_t1, col_t2 = st.columns([3, 1])
    with col_t2:
        if st.button("➕ Add Another Plant / Taxon", use_container_width=True):
            new_idx = len(st.session_state.taxa) + 1
            st.session_state.taxa.append({
                'name': f'Study Taxon {chr(64 + new_idx)}',
                'symbol': 'o',
                'color': '#2CA02C',
                'specimens': [{'label': f'Specimen {new_idx}', 'lat_str': '11.0', 'lon_str': '77.0', 'status': 'Voucher', 'alt_m': 250}]
            })
            st.rerun()

    # Iterate through Taxa
    for t_idx, taxon in enumerate(st.session_state.taxa):
        with st.expander(f"🌿 Taxon {t_idx + 1}: {taxon['name']}", expanded=True):
            c1, c2, c3, c4 = st.columns([3, 2, 2, 1])
            with c1:
                taxon['name'] = st.text_input("Taxon Scientific Name", value=taxon['name'], key=f"t_name_{t_idx}")
            with c2:
                taxon['symbol'] = st.selectbox("Marker Symbol", ["* (Star)", "^ (Triangle)", "o (Circle)", "s (Square)", "D (Diamond)", "X (Cross)"], 
                                               index=0 if taxon['symbol']=='*' else 1 if taxon['symbol']=='^' else 2, key=f"t_sym_{t_idx}")[0]
            with c3:
                taxon['color'] = st.color_picker("Marker Color", value=taxon['color'], key=f"t_col_{t_idx}")
            with c4:
                if len(st.session_state.taxa) > 1:
                    if st.button("🗑️ Remove", key=f"del_t_{t_idx}"):
                        st.session_state.taxa.pop(t_idx)
                        st.rerun()
            
            st.markdown("**Collection Localities / Specimens for this Taxon:**")
            for s_idx, spec in enumerate(taxon['specimens']):
                sc1, sc2, sc3, sc4, sc5, sc6 = st.columns([3, 2, 2, 2, 1.5, 1])
                with sc1:
                    spec['label'] = st.text_input("Locality Name", value=spec['label'], key=f"s_lbl_{t_idx}_{s_idx}")
                with sc2:
                    spec['lat_str'] = st.text_input("Latitude (DD or DMS)", value=spec['lat_str'], key=f"s_lat_{t_idx}_{s_idx}")
                with sc3:
                    spec['lon_str'] = st.text_input("Longitude (DD or DMS)", value=spec['lon_str'], key=f"s_lon_{t_idx}_{s_idx}")
                with sc4:
                    spec['status'] = st.selectbox("Type Status", ["Holotype", "Isotype", "Paratype", "Lectotype", "Syntype", "Topotype", "Voucher"], 
                                                  index=0 if spec['status']=='Holotype' else 2 if spec['status']=='Paratype' else 6, key=f"s_st_{t_idx}_{s_idx}")
                with sc5:
                    spec['alt_m'] = st.number_input("Altitude (m)", value=int(spec['alt_m']), step=10, key=f"s_alt_{t_idx}_{s_idx}")
                with sc6:
                    if len(taxon['specimens']) > 1:
                        if st.button("❌", key=f"del_s_{t_idx}_{s_idx}"):
                            taxon['specimens'].pop(s_idx)
                            st.rerun()
            
            if st.button(f"➕ Add Locality to {taxon['name']}", key=f"add_s_{t_idx}"):
                taxon['specimens'].append({
                    'label': f'New Collection Site',
                    'lat_str': '10.5',
                    'lon_str': '78.5',
                    'status': 'Additional Specimen',
                    'alt_m': 100
                })
                st.rerun()

with tab_interactive:
    st.subheader("Interactive Waypoint Inspector & Coordinate Picker")
    st.info("Click anywhere on the map or zoom to inspect Western Ghats / Coromandel terrain and collection coordinates.")
    
    # Create Folium Map
    m_int = folium.Map(location=[11.0, 78.0], zoom_start=7, tiles='Esri.WorldTopoMap')
    folium.TileLayer('Esri.WorldShadedRelief', name='Shaded Relief').add_to(m_int)
    folium.TileLayer('Esri.WorldImagery', name='Satellite').add_to(m_int)
    
    # Plot all specimens
    for taxon in st.session_state.taxa:
        for spec in taxon['specimens']:
            try:
                lat = dms_to_dd(spec['lat_str'])
                lon = dms_to_dd(spec['lon_str'])
                folium.Marker(
                    location=[lat, lon],
                    popup=f"<b>{taxon['name']}</b><br>{spec['label']}<br>{lat:.4f}°N, {lon:.4f}°E<br>Alt: {spec['alt_m']}m ({spec['status']})",
                    tooltip=f"{taxon['name']}: {spec['label']}",
                    icon=folium.Icon(color='red' if 'red' in taxon['color'].lower() or taxon['color']=='#D7191C' else 'blue')
                ).add_to(m_int)
            except Exception:
                pass
                
    folium.LayerControl().add_to(m_int)
    st.components.v1.html(m_int._repr_html_(), height=500)

with tab_preview:
    st.subheader("Publication Map Preview (300 DPI High-Resolution)")
    
    # Parse all coordinates to calculate bounding box
    all_lats, all_lons = [], []
    valid_points = []
    
    for taxon in st.session_state.taxa:
        for spec in taxon['specimens']:
            try:
                lat = dms_to_dd(spec['lat_str'])
                lon = dms_to_dd(spec['lon_str'])
                all_lats.append(lat)
                all_lons.append(lon)
                valid_points.append({
                    'taxon': taxon['name'],
                    'symbol': taxon['symbol'],
                    'color': taxon['color'],
                    'label': spec['label'],
                    'lat': lat,
                    'lon': lon,
                    'status': spec['status'],
                    'alt': spec['alt_m'],
                    'lat_dms': dd_to_dms(lat, True),
                    'lon_dms': dd_to_dms(lon, False)
                })
            except Exception as e:
                st.error(f"Error parsing coordinate for {spec['label']}: {e}")

    # Set map bounds
    lon_min, lon_max = 74.4, 80.8
    lat_min, lat_max = 8.0, 14.2
    study_box = box(lon_min, lat_min, lon_max, lat_max)

    # Render Matplotlib Figure
    fig = plt.figure(figsize=(11.5, 12.0), facecolor='white')
    ax = fig.add_axes([0.08, 0.08, 0.88, 0.86])
    ax.set_facecolor('#dbeaf8')

    # Color themes
    if "Nordic Monochromatic" in theme_choice:
        colors_hyps = [(0.0, '#f0f0f0'), (0.3, '#d9d9d9'), (0.6, '#bdbdbd'), (0.8, '#737373'), (1.0, '#252525')]
    elif "Coromandel" in theme_choice:
        colors_hyps = [(0.0, '#e5f5e0'), (0.2, '#fff7bc'), (0.5, '#fec44f'), (0.8, '#d95f0e'), (1.0, '#4a1400')]
    elif "Swiss" in theme_choice:
        colors_hyps = [(0.0, '#c7e9c0'), (0.2, '#fed976'), (0.5, '#fd8d3c'), (0.8, '#e6550d'), (1.0, '#361d15')]
    else: # Phytotaxa standard
        colors_hyps = [(0.0, '#a1d99b'), (0.04, '#c7e9c0'), (0.12, '#edf8b1'), (0.24, '#fed976'),
                       (0.40, '#feb24c'), (0.60, '#fd8d3c'), (0.76, '#e6550d'), (0.90, '#a63603'), (1.00, '#4a1400')]
    
    cmap_hyp = LinearSegmentedColormap.from_list('dyn_hyps', [(p, c) for p, c in colors_hyps], N=256)

    # Crop and process DEM
    h_s, w_s = dem_south.shape
    px_min = int((lon_min - meta_south['lon_left']) / (meta_south['lon_right'] - meta_south['lon_left']) * w_s)
    px_max = int((lon_max - meta_south['lon_left']) / (meta_south['lon_right'] - meta_south['lon_left']) * w_s)
    py_min = int((meta_south['lat_top'] - lat_max) / (meta_south['lat_top'] - meta_south['lat_bottom']) * h_s)
    py_max = int((meta_south['lat_top'] - lat_min) / (meta_south['lat_top'] - meta_south['lat_bottom']) * h_s)

    dem_crop = dem_south[py_min:py_max, px_min:px_max]
    dem_smooth = gaussian_filter(dem_crop, sigma=1.0)
    dy_m = ((lat_max - lat_min) * 110574.0) / dem_crop.shape[0]
    dx_m = ((lon_max - lon_min) * 109280.0) / dem_crop.shape[1]
    zy = sobel(dem_smooth, axis=0) / (8.0 * dy_m)
    zx = sobel(dem_smooth, axis=1) / (8.0 * dx_m)
    slope = np.arctan(np.sqrt(zx**2 + zy**2))
    aspect = np.arctan2(-zy, zx)
    def calc_hs(s, a, alt, az):
        return np.clip(np.sin(np.radians(alt))*np.cos(s) + np.cos(np.radians(alt))*np.sin(s)*np.cos(np.radians(az) - a), 0, 1)
    hs = 0.7 * calc_hs(slope, aspect, 45, 315) + 0.3 * calc_hs(slope, aspect, 35, 225)
    hs = (hs - hs.min()) / (hs.max() - hs.min() + 1e-5)

    elev_c = np.clip(dem_crop, 0, 2600)
    rgb_hyp = cmap_hyp(elev_c / 2600.0)[:, :, :3]
    blended_land = np.clip(rgb_hyp * (0.40 + 0.60 * hs[:, :, np.newaxis]) * 1.15, 0, 1)

    # Vector Land Clipping for silky smooth coasts
    india_study = india_highres.clip(study_box)
    sl_study = land_10m.clip(study_box)
    comb_land = india_study.geometry.union_all()
    if show_sl and len(sl_study) > 0:
        comb_land = comb_land.union(sl_study.geometry.union_all())
    
    path_land = shapely_to_mpl_path(comb_land)
    im_relief = ax.imshow(blended_land, extent=[lon_min, lon_max, lat_min, lat_max], origin='upper', interpolation='bicubic', zorder=2)
    if path_land:
        c_patch = PathPatch(path_land, facecolor='none', edgecolor='none', transform=ax.transData)
        ax.add_patch(c_patch)
        im_relief.set_clip_path(c_patch)

    # Outlines
    india_study.boundary.plot(ax=ax, color='#262626', linewidth=1.1, zorder=5)
    if show_sl and len(sl_study) > 0:
        sl_study.boundary.plot(ax=ax, color='#444444', linewidth=1.0, zorder=5)

    if show_districts:
        dist_s = districts_gdf[districts_gdf.intersects(study_box)]
        dist_s.boundary.plot(ax=ax, color='#666666', linewidth=0.55, linestyle=':', alpha=0.50, zorder=3)

    if highlight_districts:
        # Find districts matching the points
        for pt in valid_points:
            p_geom = Point(pt['lon'], pt['lat'])
            m_dist = districts_gdf[districts_gdf.contains(p_geom)]
            if len(m_dist) > 0:
                m_dist.boundary.plot(ax=ax, color=pt['color'], linewidth=1.2, linestyle='--', alpha=0.85, zorder=4)

    states_study = states_gdf[states_gdf.intersects(study_box)]
    states_study.boundary.plot(ax=ax, color='#222222', linewidth=1.4, linestyle='-', zorder=5)

    if show_rivers:
        rivers_study = rivers_gdf[rivers_gdf.intersects(study_box)]
        rivers_study.plot(ax=ax, color='#1f78b4', linewidth=0.9, alpha=0.85, zorder=4)

    if show_places:
        ax.text(78.5, 11.2, "TAMIL NADU", fontsize=13, fontweight='bold', color='#1a1a1a', alpha=0.85, zorder=6, ha='center')
        ax.text(76.3, 9.8, "KERALA", fontsize=12, fontweight='bold', color='#1a1a1a', alpha=0.85, zorder=6, ha='center', rotation=70)
        ax.text(76.5, 13.2, "KARNATAKA", fontsize=12, fontweight='bold', color='#1a1a1a', alpha=0.85, zorder=6, ha='center')
        ax.text(79.3, 13.6, "ANDHRA PRADESH", fontsize=11, fontweight='bold', color='#1a1a1a', alpha=0.85, zorder=6, ha='center')
        ax.text(75.2, 9.5, "ARABIAN SEA", fontsize=13, fontweight='bold', color='#3b6989', fontstyle='italic', zorder=6)
        ax.text(79.7, 12.3, "BAY OF BENGAL", fontsize=12, fontweight='bold', color='#3b6989', fontstyle='italic', zorder=6)
        if show_sl:
            ax.text(80.5, 8.8, "SRI LANKA", fontsize=10, fontweight='bold', color='#444444', fontstyle='italic', zorder=6)

    if show_mountains:
        ax.text(75.3, 11.8, "WESTERN GHATS", fontsize=10, fontweight='bold', color='#5c2e0b', fontstyle='italic', rotation=-45, zorder=6)
        ax.text(76.8, 11.5, "Nilgiri Hills", fontsize=8.5, color='#421e05', fontstyle='italic', zorder=6)
        ax.text(76.9, 10.3, "Anamalai Hills", fontsize=8.5, color='#421e05', fontstyle='italic', zorder=6)
        ax.text(76.9, 10.75, "Palakkad Gap", fontsize=8, color='#003366', fontweight='bold', zorder=6)

    # Plot Specimen Localities & Callouts
    for pt in valid_points:
        ax.scatter([pt['lon']], [pt['lat']], s=220, marker=pt['symbol'], facecolor=pt['color'], edgecolor='black', linewidth=1.5, zorder=10)
        ax.scatter([pt['lon']], [pt['lat']], s=75, marker=pt['symbol'], facecolor='white', edgecolor='none', zorder=11)
        
        # Offsets
        ox = 0.35 if pt['lon'] > 78.0 else -1.85
        oy = -0.70 if pt['lon'] > 78.0 else 0.65
        c_text = f"$\\mathbf{{{pt['label']}}}$\n{pt['lat']:.4f}°N, {pt['lon']:.4f}°E\n({pt['lat_dms']}, {pt['lon_dms']})\nAlt: {pt['alt']} m | {pt['status']}"
        ax.annotate(
            c_text, xy=(pt['lon'], pt['lat']), xytext=(pt['lon'] + ox, pt['lat'] + oy),
            fontsize=8.2, fontfamily='sans-serif',
            bbox=dict(boxstyle="round,pad=0.4", facecolor='white', edgecolor=pt['color'], linewidth=1.3, alpha=0.96),
            arrowprops=dict(arrowstyle="->", color=pt['color'], linewidth=1.3),
            zorder=15
        )

    if show_scalebar:
        sb_x0, sb_y0 = 74.80, 8.25
        km50_deg = 50.0 / 110.1
        ax.add_patch(Rectangle((sb_x0, sb_y0), km50_deg, 0.04, facecolor='black', edgecolor='black', linewidth=0.8, zorder=12))
        ax.add_patch(Rectangle((sb_x0 + km50_deg, sb_y0), km50_deg, 0.04, facecolor='white', edgecolor='black', linewidth=0.8, zorder=12))
        ax.add_patch(Rectangle((sb_x0 + 2*km50_deg, sb_y0), km50_deg, 0.04, facecolor='black', edgecolor='black', linewidth=0.8, zorder=12))
        ax.text(sb_x0, sb_y0 + 0.06, "0", fontsize=8, ha='center', fontweight='bold', zorder=12)
        ax.text(sb_x0 + km50_deg, sb_y0 + 0.06, "50", fontsize=8, ha='center', fontweight='bold', zorder=12)
        ax.text(sb_x0 + 2*km50_deg, sb_y0 + 0.06, "100", fontsize=8, ha='center', fontweight='bold', zorder=12)
        ax.text(sb_x0 + 3*km50_deg, sb_y0 + 0.06, "150 km", fontsize=8, ha='center', fontweight='bold', zorder=12)
        ax.add_patch(FancyBboxPatch((sb_x0 - 0.15, sb_y0 - 0.10), 3*km50_deg + 0.45, 0.28, boxstyle="round,pad=0.04", facecolor='white', edgecolor='#666666', linewidth=0.8, alpha=0.92, zorder=11))

    if show_compass:
        nx, ny = 74.85, 13.65
        ax.annotate('N', xy=(nx, ny + 0.28), fontsize=12, fontweight='bold', ha='center', va='center', zorder=15)
        ax.add_patch(MplPolygon([(nx, ny + 0.22), (nx - 0.08, ny), (nx, ny - 0.05)], facecolor='black', edgecolor='black', linewidth=1.0, zorder=14))
        ax.add_patch(MplPolygon([(nx, ny + 0.22), (nx + 0.08, ny), (nx, ny - 0.05)], facecolor='white', edgecolor='black', linewidth=1.0, zorder=14))
        ax.add_patch(FancyBboxPatch((nx - 0.20, ny - 0.10), 0.40, 0.48, boxstyle="round,pad=0.03", facecolor='white', edgecolor='#666666', linewidth=0.8, alpha=0.92, zorder=13))

    if show_elev_bar:
        ax.add_patch(FancyBboxPatch((78.95, 8.15), 1.70, 0.70, boxstyle="round,pad=0.04", facecolor='white', edgecolor='#666666', linewidth=0.8, alpha=0.92, zorder=11))
        ax.text(79.80, 8.70, "Elevation (m a.s.l.)", fontsize=8.5, fontweight='bold', ha='center', zorder=13)
        cb_x0, cb_y0 = 79.15, 8.42
        cb_w, cb_h = 1.30, 0.08
        grad = np.linspace(0, 1, 256).reshape(1, -1)
        ax.imshow(grad, cmap=cmap_hyp, extent=[cb_x0, cb_x0 + cb_w, cb_y0, cb_y0 + cb_h], zorder=12)
        ax.add_patch(Rectangle((cb_x0, cb_y0), cb_w, cb_h, facecolor='none', edgecolor='black', linewidth=0.8, zorder=13))
        for elev_val, lbl in [(0, "0"), (500, "500"), (1000, "1000"), (1800, "1800"), (2600, "2600m")]:
            tx = cb_x0 + (elev_val / 2600.0) * cb_w
            ax.plot([tx, tx], [cb_y0, cb_y0 - 0.025], color='black', linewidth=0.8, zorder=13)
            ax.text(tx, cb_y0 - 0.07, lbl, fontsize=7, ha='center', zorder=13)

    if show_legend:
        leg_bg = FancyBboxPatch((74.65, 9.35), 2.25, 1.45, boxstyle="round,pad=0.04", facecolor='white', edgecolor='#444444', linewidth=0.9, alpha=0.94, zorder=11)
        ax.add_patch(leg_bg)
        ax.text(75.77, 10.60, "MAP LEGEND", fontsize=9, fontweight='bold', ha='center', zorder=13)
        y_pos = 10.35
        for pt in valid_points[:3]:
            ax.scatter([74.85], [y_pos], s=100, marker=pt['symbol'], facecolor=pt['color'], edgecolor='black', linewidth=0.8, zorder=13)
            ax.text(75.05, y_pos - 0.03, f"{pt['taxon']}", fontsize=8, va='center', zorder=13)
            y_pos -= 0.25

    ax.set_xlim(lon_min, lon_max)
    ax.set_ylim(lat_min, lat_max)
    ax.set_aspect('equal')
    ax.set_xticks(np.arange(75.0, 81.0, 1.0))
    ax.set_yticks(np.arange(8.0, 15.0, 1.0))
    ax.set_xticklabels([f"{int(x)}°E" for x in np.arange(75.0, 81.0, 1.0)], fontsize=9, fontweight='bold')
    ax.set_yticklabels([f"{int(y)}°N" for y in np.arange(8.0, 15.0, 1.0)], fontsize=9, fontweight='bold')
    ax.grid(True, linestyle='--', linewidth=0.5, color='#999999', alpha=0.40, zorder=7)
    for spine in ax.spines.values():
        spine.set_edgecolor('black')
        spine.set_linewidth(1.3)

    # Inset Map of India
    if show_inset:
        # Determine inset coords
        if inset_pos == "Top-Right": ix, iy = 0.62, 0.62
        elif inset_pos == "Top-Left": ix, iy = 0.10, 0.62
        elif inset_pos == "Bottom-Right": ix, iy = 0.62, 0.10
        else: ix, iy = 0.10, 0.10

        ax_in = fig.add_axes([ix, iy, 0.32, 0.30])
        ax_in.set_facecolor('#dbeaf8')
        in_l_min, in_l_max, in_b_min, in_b_max = 67.5, 98.0, 6.0, 37.5
        ibox = box(in_l_min, in_b_min, in_l_max, in_b_max)
        
        im_in = ax_in.imshow(raster_india, extent=[meta_india['lon_left'], meta_india['lon_right'], meta_india['lat_bottom'], meta_india['lat_top']],
                             origin='upper', interpolation='bicubic', zorder=1)
        
        land_in = land_10m[land_10m.intersects(ibox)].clip(ibox)
        all_in_land = land_in.geometry.union_all().union(india_highres.geometry.union_all())
        p_in = shapely_to_mpl_path(all_in_land)
        if p_in:
            cp_in = PathPatch(p_in, facecolor='none', edgecolor='none', transform=ax_in.transData)
            ax_in.add_patch(cp_in)
            im_in.set_clip_path(cp_in)

        ne_countries[ne_countries['SOVEREIGNT'] != 'India'].clip(ibox).plot(ax=ax_in, facecolor='#eae6df', edgecolor='#777777', linewidth=0.4, linestyle='--', zorder=2)
        states_gdf.plot(ax=ax_in, facecolor='none', edgecolor='#666666', linewidth=0.35, zorder=4)
        india_highres.boundary.plot(ax=ax_in, color='#000000', linewidth=1.2, zorder=6)

        ax_in.text(77.0, 35.0, "LADAKH", fontsize=5.5, fontweight='bold', color='#222222', ha='center', zorder=7)
        ax_in.text(74.5, 33.5, "J&K", fontsize=5, fontweight='bold', color='#222222', ha='center', zorder=7)
        ax_in.text(94.5, 28.2, "ARUNACHAL\nPRADESH", fontsize=4.5, fontweight='bold', color='#222222', ha='center', zorder=7)

        ax_in.add_patch(Rectangle((lon_min, lat_min), lon_max - lon_min, lat_max - lat_min, facecolor='#ff0000', edgecolor='#b30000', linewidth=1.5, alpha=0.30, zorder=8))
        ax_in.text(82.5, 36.8, "INDIA\n(Survey of India Boundary)", fontsize=7, fontweight='bold', color='#000000', ha='center', va='top', bbox=dict(boxstyle='round,pad=0.2', facecolor='white', edgecolor='#444444', linewidth=0.6, alpha=0.92), zorder=11)
        ax_in.set_xlim(in_l_min, in_l_max)
        ax_in.set_ylim(in_b_min, in_b_max)
        ax_in.set_aspect('equal')
        ax_in.set_xticks([70, 80, 90])
        ax_in.set_yticks([10, 20, 30])
        ax_in.set_xticklabels(['70°E', '80°E', '90°E'], fontsize=6)
        ax_in.set_yticklabels(['10°N', '20°N', '30°N'], fontsize=6)
        ax_in.tick_params(axis='both', which='both', length=2.5, pad=1.5)
        for spine in ax_in.spines.values():
            spine.set_edgecolor('#222222')
            spine.set_linewidth(1.1)

    fig.text(0.50, 0.975, "Geographic Distribution of Study Localities", fontsize=14, fontweight='bold', ha='center', va='top')
    fig.text(0.50, 0.953, "Peninsular India Topographic Relief Map with Survey of India Administrative Boundaries", fontsize=10, fontstyle='italic', ha='center', va='top', color='#333333')

    # Display Figure
    st.pyplot(fig)

    # Save to buffers for download
    buf_png = io.BytesIO()
    fig.savefig(buf_png, format='png', dpi=300, facecolor='white', bbox_inches='tight')
    buf_png.seek(0)

    buf_svg = io.BytesIO()
    fig.savefig(buf_svg, format='svg', facecolor='white', bbox_inches='tight')
    buf_svg.seek(0)

    buf_pdf = io.BytesIO()
    fig.savefig(buf_pdf, format='pdf', facecolor='white', bbox_inches='tight')
    buf_pdf.seek(0)
    plt.close(fig)

    # Export Buttons
    col_d1, col_d2, col_d3 = st.columns(3)
    with col_d1:
        st.download_button("📥 Download Camera-Ready PNG (300 DPI)", data=buf_png, file_name="Taxonomy_Map_300DPI.png", mime="image/png", use_container_width=True)
    with col_d2:
        st.download_button("📥 Download Vector SVG (Editable Paths)", data=buf_svg, file_name="Taxonomy_Map_Vector.svg", mime="image/svg+xml", use_container_width=True)
    with col_d3:
        st.download_button("📥 Download Camera-Ready PDF", data=buf_pdf, file_name="Taxonomy_Map_Publication.pdf", mime="application/pdf", use_container_width=True)

    # Automated Manuscript Figure Caption
    st.markdown("### 📝 Auto-Generated Manuscript Caption (*Phytotaxa / Rheedea Style*)")
    taxa_names = ", ".join([f"*{t['name']}*" for t in st.session_state.taxa])
    caption_text = (
        f"FIGURE 1. Geographic distribution of {taxa_names} in southern India. "
        f"Topographic relief map displaying collection localities with multi-directional shaded relief and hypsometric elevation tinting. "
        f"Solid lines indicate official state boundaries; dotted lines indicate district boundaries; hydrographic networks denote major river systems. "
        + ("Inset displays geographic position within the Republic of India conforming to official Survey of India administrative boundaries (including Jammu & Kashmir, Ladakh, and Arunachal Pradesh). " if show_inset else "")
        + "Digital elevation derived from SRTM/GMTED (300 DPI)."
    )
    st.code(caption_text, language="text")

