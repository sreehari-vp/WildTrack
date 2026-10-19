# ruff: noqa: E501
"""Derive reproducible analytical land-cover zones from the Phase 1 study regions.

These are thematic land-cover classes, not legal, hazard, or habitat-suitability
determinations. WorldCover 2021 is a modelled 10 m snapshot.
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import rasterio
from pyproj import Geod
from rasterio.features import geometry_mask, shapes
from rasterio.windows import from_bounds
from shapely.geometry import MultiPolygon, mapping, shape
from shapely.ops import unary_union

ROOT = Path(__file__).resolve().parents[1]
REGIONS_PATH = ROOT / "data/research/phase1-study-regions.geojson"
RASTER_PATH = ROOT / "data/research/ooty-worldcover-2021.tif"
OUTPUT_PATH = ROOT / "data/research/phase2-landcover-zones.geojson"
SOURCE_META_PATH = ROOT / "data/research/ooty-worldcover-2021.json"
CLASS_GROUPS = {
    "tree_cover": {10},
    "shrubland": {20},
    "grassland": {30},
    "cultivated_land": {40},
    "built_up": {50},
    "bare_or_sparse_cover": {60},
    "surface_water": {80, 90},
}
LABELS = {
    "tree_cover": ("Tree cover", "ESA WorldCover class 10; modelled tree-cover pixels."),
    "shrubland": ("Shrubland", "ESA WorldCover class 20; modelled shrubland pixels."),
    "grassland": ("Grassland", "ESA WorldCover class 30; modelled grassland pixels."),
    "cultivated_land": ("Cultivated land", "ESA WorldCover class 40; modelled cropland pixels."),
    "built_up": ("Built-up footprint", "ESA WorldCover class 50; modelled built-up pixels, not a complete settlement boundary."),
    "bare_or_sparse_cover": ("Bare or sparse cover", "ESA WorldCover class 60; not proof of rocky terrain."),
    "surface_water": ("Water or wetland", "ESA WorldCover classes 80 and 90; modelled permanent water and herbaceous wetland pixels."),
}
GEOD = Geod(ellps="WGS84")


def geodesic_area_km2(geometry) -> float:
    return abs(GEOD.geometry_area_perimeter(geometry)[0]) / 1_000_000


def polygonal(geometry):
    if geometry.geom_type == "Polygon":
        return MultiPolygon([geometry])
    if geometry.geom_type == "MultiPolygon":
        return geometry
    parts = [part for part in getattr(geometry, "geoms", []) if part.geom_type == "Polygon"]
    return MultiPolygon(parts)


def main() -> None:
    region_doc = json.loads(REGIONS_PATH.read_text(encoding="utf-8"))
    source_meta = json.loads(SOURCE_META_PATH.read_text(encoding="utf-8"))
    output_features = []
    with rasterio.open(RASTER_PATH) as raster:
        raster_bounds = shape({
            "type": "Polygon",
            "coordinates": [[
                [raster.bounds.left, raster.bounds.bottom],
                [raster.bounds.right, raster.bounds.bottom],
                [raster.bounds.right, raster.bounds.top],
                [raster.bounds.left, raster.bounds.top],
                [raster.bounds.left, raster.bounds.bottom],
            ]],
        })
        for region_feature in region_doc["features"]:
            region = shape(region_feature["geometry"])
            clipped_region = region.intersection(raster_bounds)
            if clipped_region.is_empty:
                continue
            coverage_pct = min(100.0, geodesic_area_km2(clipped_region) / geodesic_area_km2(region) * 100)
            minx, miny, maxx, maxy = clipped_region.bounds
            window = from_bounds(minx, miny, maxx, maxy, raster.transform).round_offsets().round_lengths()
            values = raster.read(1, window=window)
            window_transform = raster.window_transform(window)
            inside_region = geometry_mask(
                [mapping(clipped_region)],
                out_shape=values.shape,
                transform=window_transform,
                invert=True,
                all_touched=False,
            )
            for zone_code, source_classes in CLASS_GROUPS.items():
                selected = inside_region
                selected = selected & np.isin(values, list(source_classes))
                if not selected.any():
                    continue
                polygons = [
                    shape(geometry)
                    for geometry, value in shapes(values, mask=selected, transform=window_transform)
                    if int(value) in source_classes
                ]
                merged = unary_union(polygons).intersection(clipped_region)
                if merged.is_empty:
                    continue
                # Remove isolated mapping noise below 1,000 m², then simplify ~5 m.
                parts = [part for part in getattr(merged, "geoms", [merged]) if part.area > 0]
                parts = [part for part in parts if abs(GEOD.geometry_area_perimeter(part)[0]) >= 1000]
                if not parts:
                    continue
                merged = unary_union(parts).simplify(0.00005, preserve_topology=True)
                multipolygon = polygonal(merged)
                if multipolygon.is_empty:
                    continue
                label, rationale = LABELS[zone_code]
                output_features.append({
                    "type": "Feature",
                    "id": f"{region_feature['properties']['code']}:{zone_code}",
                    "geometry": mapping(multipolygon),
                    "properties": {
                        "code": f"{region_feature['properties']['code']}:{zone_code}",
                        "region_code": region_feature["properties"]["code"],
                        "name": f"{region_feature['properties']['name']} — {label}",
                        "zone_type": zone_code,
                        "description": rationale,
                        "data_source": "ESA WorldCover 10 m 2021 v200",
                        "source_url": source_meta["source_url"],
                        "source_doi": source_meta["doi"],
                        "source_license": source_meta["licence"],
                        "resolution_m": 10,
                        "minimum_component_area_m2": 1000,
                        "simplification_tolerance_degrees": 0.00005,
                        "legal_status": "analytical_landcover_class",
                        "area_sq_km": round(geodesic_area_km2(multipolygon), 3),
                        "raster_coverage_pct_of_region": round(coverage_pct, 2),
                    },
                })
    OUTPUT_PATH.write_text(json.dumps({"type": "FeatureCollection", "features": output_features}, separators=(",", ":")) + "\n", encoding="utf-8")
    print(json.dumps({"regions": len(region_doc["features"]), "landcover_zone_features": len(output_features), "zone_types": sorted({feature["properties"]["zone_type"] for feature in output_features}), "output": str(OUTPUT_PATH)}, indent=2))


if __name__ == "__main__":
    main()
