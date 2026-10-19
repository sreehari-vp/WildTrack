"""Print nearby Survey of India forest features around Ooty reference locations."""

import json
import math
from pathlib import Path

from shapely.geometry import Point, shape
from shapely.ops import nearest_points

CENTERS = {
    "Ooty North / Marlimund": (76.70, 11.43),
    "Doddabetta Peak": (76.73568, 11.40069),
    "Pykara River": (76.59106, 11.49031),
    "Avalanche Lake": (76.611, 11.322),
    "Upper Bhavani Dam": (76.52, 11.23),
    "Mukurthi Park interior": (76.50, 11.27),
}
features = json.loads(Path("data/research/nilgiris-soi-forest-features.geojson").read_text())["features"]
geometries = [(feature["properties"], shape(feature["geometry"])) for feature in features]
for label, (lon, lat) in CENTERS.items():
    point = Point(lon, lat)
    scored = []
    for properties, geometry in geometries:
        near_point, near_geom = nearest_points(point, geometry)
        dlon = (near_point.x - near_geom.x) * 111_320 * math.cos(math.radians(lat))
        dlat = (near_point.y - near_geom.y) * 111_320
        distance = math.hypot(dlon, dlat)
        scored.append((distance, properties))
    print(label)
    for distance, properties in sorted(scored, key=lambda item: item[0])[:4]:
        print(f"  {distance:.0f} m | {properties['name'].strip()} | {properties['type']} | {properties['source_area_m2']/1e6:.3f} km2")
