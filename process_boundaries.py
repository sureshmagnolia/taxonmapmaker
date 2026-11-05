import json
import geopandas as gpd
from shapely.geometry import shape
from shapely.ops import unary_union

gdf = gpd.read_file(r"C:\Users\sures\.gemini\antigravity\scratch\india_taxonomy_map\data\india_states_soi.geojson")
print(f"Loaded {len(gdf)} features from SOI GeoJSON.")
print("CRS:", gdf.crs)

# Check state column
st_col = 'st_nm'
unique_states = sorted(gdf[st_col].unique())
print(f"Total States/UTs: {len(unique_states)}")

# Dissolve by state
states_gdf = gdf.dissolve(by=st_col).reset_index()
print(f"Dissolved into {len(states_gdf)} states.")
states_gdf.to_file(r"C:\Users\sures\.gemini\antigravity\scratch\india_taxonomy_map\data\india_states_clean.geojson", driver="GeoJSON")

# Exterior country boundary
country_geom = unary_union(states_gdf.geometry)
country_gdf = gpd.GeoDataFrame([{'name': 'India'}], geometry=[country_geom], crs=gdf.crs)
country_gdf.to_file(r"C:\Users\sures\.gemini\antigravity\scratch\india_taxonomy_map\data\india_country_clean.geojson", driver="GeoJSON")
print("Saved clean states and country boundaries successfully!")

