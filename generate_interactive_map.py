import os
import json
import folium
from folium import plugins

out_dir = r"C:\Users\sures\.gemini\antigravity\scratch\india_taxonomy_map\figures"
art_dir = r"C:\Users\sures\.gemini\antigravity\brain\5da3f0cc-02b5-4025-92d0-34a0d8ef8ca6"

loc1_lat, loc1_lon = 10.7870, 79.1378
loc2_lat, loc2_lon = 11.067917, 76.560250

# Center between the two points
center_lat = (loc1_lat + loc2_lat) / 2.0
center_lon = (loc1_lon + loc2_lon) / 2.0

m = folium.Map(
    location=[center_lat, center_lon],
    zoom_start=8,
    tiles='Esri.WorldTopoMap',
    name='Esri World Topographic'
)

# Additional Basemaps
folium.TileLayer('Esri.WorldShadedRelief', name='Esri Shaded Relief').add_to(m)
folium.TileLayer('Esri.WorldImagery', name='Esri Satellite Imagery').add_to(m)
folium.TileLayer('OpenStreetMap', name='OpenStreetMap Standard').add_to(m)

# Load SOI boundaries
with open(r"C:\Users\sures\.gemini\antigravity\scratch\india_taxonomy_map\data\india_states_smooth.geojson", "r", encoding="utf-8") as f:
    states_geojson = json.load(f)

folium.GeoJson(
    states_geojson,
    name='Official State Boundaries (SOI)',
    style_function=lambda x: {
        'color': '#222222',
        'weight': 2.0,
        'fillOpacity': 0.05,
        'fillColor': '#ffffff',
        'dashArray': '4, 4'
    },
    tooltip=folium.GeoJsonTooltip(fields=['st_nm'], aliases=['State/UT:'])
).add_to(m)

# Marker 1: Thanjavur
popup_html1 = """
<div style="font-family: Arial, sans-serif; font-size: 13px; line-height: 1.5; min-width: 240px;">
    <h4 style="margin: 0 0 6px 0; color: #b30000; border-bottom: 2px solid #b30000; padding-bottom: 4px;">Locality 1: Thanjavur</h4>
    <b>Decimal:</b> 10.7870°N, 79.1378°E<br>
    <b>DMS:</b> 10°47'13.2"N, 79°08'16.1"E<br>
    <b>District:</b> Thanjavur<br>
    <b>State:</b> Tamil Nadu, India<br>
    <b>Elevation:</b> ~59 m a.s.l.<br>
    <b>Ecoregion:</b> Cauvery Delta / Coromandel Coastal Plain
</div>
"""
folium.Marker(
    location=[loc1_lat, loc1_lon],
    popup=folium.Popup(popup_html1, max_width=300),
    tooltip="Locality 1: Thanjavur (10.7870°N, 79.1378°E)",
    icon=folium.Icon(color='red', icon='star', prefix='fa')
).add_to(m)

# Marker 2: Palakkad / Attappadi
popup_html2 = """
<div style="font-family: Arial, sans-serif; font-size: 13px; line-height: 1.5; min-width: 240px;">
    <h4 style="margin: 0 0 6px 0; color: #0044cc; border-bottom: 2px solid #0044cc; padding-bottom: 4px;">Locality 2: Attappadi / Palakkad</h4>
    <b>Decimal:</b> 11.0679°N, 76.5603°E<br>
    <b>DMS:</b> 11°04'04.5"N, 76°33'36.9"E<br>
    <b>District:</b> Palakkad<br>
    <b>State:</b> Kerala, India<br>
    <b>Elevation:</b> ~572 m a.s.l.<br>
    <b>Ecoregion:</b> Western Ghats (Silent Valley buffer / Nilgiris foothills)
</div>
"""
folium.Marker(
    location=[loc2_lat, loc2_lon],
    popup=folium.Popup(popup_html2, max_width=300),
    tooltip="Locality 2: Palakkad (11°04'04.5\"N, 76°33'36.9\"E)",
    icon=folium.Icon(color='blue', icon='info-sign')
).add_to(m)

# Geodesic Line between the two points
line = folium.PolyLine(
    locations=[[loc1_lat, loc1_lon], [loc2_lat, loc2_lon]],
    color='#e65100',
    weight=2.5,
    dash_array='6, 6',
    tooltip="Direct distance: ~282.4 km"
)
line.add_to(m)

# Add Measurement control, Fullscreen, and Layer Control
plugins.MeasureControl(position='topleft', primary_length_unit='kilometers').add_to(m)
plugins.Fullscreen(position='topright').add_to(m)
folium.LayerControl(position='topright', collapsed=False).add_to(m)

html_path1 = os.path.join(out_dir, "taxonomy_map_interactive.html")
html_path2 = os.path.join(art_dir, "taxonomy_map_interactive.html")
m.save(html_path1)
m.save(html_path2)
print("Saved interactive HTML map successfully!")

