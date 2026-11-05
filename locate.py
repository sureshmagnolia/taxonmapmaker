import json
from shapely.geometry import shape, Point

with open(r'C:\Users\sures\.gemini\antigravity\scratch\india_taxonomy_map\data\india_states_soi.geojson', 'r', encoding='utf-8') as f:
    d = json.load(f)

# Point 1: 10.7870°N, 79.1378°E
p1 = Point(79.1378, 10.7870)

# Point 2: 11°04'04.5"N 76°33'36.9"E
# 11 + 4/60 + 4.5/3600 = 11.067917
# 76 + 33/60 + 36.9/3600 = 76.560250
p2 = Point(76.56025, 11.067917)

for feat in d['features']:
    geom = shape(feat['geometry'])
    props = feat['properties']
    if geom.contains(p1):
        print(f"Point 1 (10.7870 N, 79.1378 E): District={props.get('district')}, State={props.get('st_nm')}")
    if geom.contains(p2):
        print(f"Point 2 (11.0679 N, 76.5603 E): District={props.get('district')}, State={props.get('st_nm')}")

