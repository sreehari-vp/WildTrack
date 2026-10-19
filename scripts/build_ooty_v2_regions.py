"""Build a separate, source-backed Ooty forest-region candidate set.

No existing Phase 1/2 files or database rows are changed. Source forest
geometry is retained only inside the local WorldCover footprint, so these are
analysis boundaries rather than certified legal reserve boundaries.
"""

from __future__ import annotations

import json
from pathlib import Path

import rasterio
from pyproj import Geod
from shapely.geometry import box, mapping, shape
from shapely.ops import unary_union

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "data/research/nilgiris-soi-forest-features.geojson"
SOURCE_META = ROOT / "data/research/nilgiris-soi-forest-features.json"
RASTER = ROOT / "data/research/ooty-worldcover-2021.tif"
OUTPUT = ROOT / "data/research/ooty-v2/study-regions.geojson"
GEOD = Geod(ellps="WGS84")

# Exact labels as found in the retained Survey of India forest extract. Some
# source labels contain encoding artifacts; clean display names are separate.
REGIONS = {
    "wenlock_downs": ("Wenlock Downs", "WENLAND DOWNS RESERVED FOREST"),
    "naduvattam": ("Naduvattam Forest", "NADUVATTAM RESERVED"),
    "porthimund": ("Porthimund Forest", "PORTHIMUND RESERVED FOREST"),
    "kundah": ("Kundah Forest", "KUNDA RESERVED FOREST"),
    "mukurthi_lake": ("Mukurthi Lake Forest", "MUKURTI LAKE RESERVED FOREST"),
    "nilgiri_peak": ("Nilgiri Peak Forest", "N|LGIRI PEAK RESERVED FOREST"),
    "doddabetta_forest": ("Doddabetta Forest", "DODABETTA RESERVED FOREST"),
    "kalhatty": ("Kalhatty Forest", "KA;LHATTI RESERVED FOREST"),
}


def main() -> None:
    source = json.loads(SOURCE.read_text(encoding="utf-8"))
    source_meta = json.loads(SOURCE_META.read_text(encoding="utf-8"))
    with rasterio.open(RASTER) as raster:
        footprint = box(*raster.bounds)

    features = []
    for code, (label, source_name) in REGIONS.items():
        matching = [
            item for item in source["features"]
            if item["properties"].get("name") == source_name
            and str(item["properties"].get("type", "")).upper() == "RESERVED"
        ]
        if not matching:
            raise ValueError(f"Source forest feature missing: {source_name}")
        unique = {}
        for item in matching:
            geom = shape(item["geometry"])
            if not geom.is_valid:
                geom = geom.buffer(0)
            unique[geom.normalize().wkb] = geom
        full_geometry = unary_union(list(unique.values()))
        clipped = full_geometry.intersection(footprint)
        if clipped.is_empty:
            raise ValueError(f"{source_name} does not intersect the local WorldCover footprint")
        area_sq_km = abs(GEOD.geometry_area_perimeter(clipped)[0]) / 1_000_000
        features.append({
            "type": "Feature",
            "id": code,
            "geometry": mapping(clipped),
            "properties": {
                "code": code,
                "name": label,
                "source_name": source_name,
                "boundary_type": "Source forest polygon clipped to Ooty WorldCover study footprint",
                "data_source": source_meta["publisher"],
                "source_url": source_meta["source_url"],
                "source_license": source_meta["licence"],
                "source_sha256": source_meta["source_sha256"],
                "source_feature_count": len(unique),
                "selection_radius_m": None,
                "area_sq_km": round(area_sq_km, 3),
                "legal_status": "analytical_study_extent_not_certified_legal_boundary",
            },
        })

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(
        json.dumps({"type": "FeatureCollection", "features": features}, separators=(",", ":")) + "\n",
        encoding="utf-8",
    )
    print(json.dumps({"regions": len(features), "areas_sq_km": {
        feature["properties"]["code"]: feature["properties"]["area_sq_km"]
        for feature in features
    }, "output": str(OUTPUT)}, indent=2))


if __name__ == "__main__":
    main()
