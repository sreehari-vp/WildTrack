"""Extract Ooty-area Survey of India forest polygons from the source Parquet."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import duckdb
from shapely import from_wkb
from shapely.geometry import Point, mapping

SOURCE = Path("data/raw/soi-forests-temporary.parquet")
OUTPUT = Path("data/research/nilgiris-soi-forest-features.geojson")
BOUNDS = (76.35, 11.15, 76.90, 11.57)
CENTERS = {
    "Ooty North / Marlimund": (76.70, 11.43),
    "Doddabetta Peak": (76.73568, 11.40069),
    "Pykara River": (76.59106, 11.49031),
    "Avalanche Lake": (76.611, 11.322),
    "Upper Bhavani Dam": (76.52, 11.23),
    "Mukurthi Park interior": (76.50, 11.27),
}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as file:
        for block in iter(lambda: file.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def main() -> None:
    west, south, east, north = BOUNDS
    query = f"""
        SELECT unique_id, survey_dat, fcode, type, tree_type, addl_info,
               shape_leng, name, "shape.STArea()" AS source_area_m2,
               xmin, ymin, xmax, ymax, geometry
        FROM read_parquet(?)
        WHERE xmax >= ? AND xmin <= ? AND ymax >= ? AND ymin <= ?
    """
    rows = duckdb.connect().execute(query, [str(SOURCE), west, east, south, north]).fetchall()
    columns = ["unique_id", "survey_dat", "fcode", "type", "tree_type", "addl_info", "shape_leng", "name", "source_area_m2", "xmin", "ymin", "xmax", "ymax", "geometry"]
    features = []
    geometries = []
    for row in rows:
        record = dict(zip(columns, row, strict=True))
        geometry = from_wkb(record.pop("geometry"))
        if not geometry.is_valid:
            geometry = geometry.buffer(0)
        geometries.append((record, geometry))
        properties = {key: value for key, value in record.items() if key not in {"xmin", "ymin", "xmax", "ymax"}}
        features.append({"type": "Feature", "geometry": mapping(geometry), "properties": properties})

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(json.dumps({"type": "FeatureCollection", "features": features}, separators=(",", ":")), encoding="utf-8")

    summary = {}
    for label, (lon, lat) in CENTERS.items():
        point = Point(lon, lat)
        ranked = sorted(
            ((geometry.distance(point), record) for record, geometry in geometries),
            key=lambda item: item[0],
        )
        summary[label] = [
            {
                "distance_degrees": round(distance, 5),
                "name": record["name"],
                "type": record["type"],
                "tree_type": record["tree_type"],
                "source_area_m2": record["source_area_m2"],
                "unique_id": record["unique_id"],
            }
            for distance, record in ranked[:5]
        ]

    report = {
        "source_url": "https://pub-0429b8e3b5a946e69ea007df844a6f1c.r2.dev/environment/forests/SOI_Forests.parquet",
        "publisher": "BharatAtlas; source attribution: Survey of India",
        "licence": "CC0-1.0 as stated by BharatAtlas; source-specific metadata should be checked before any redistribution",
        "source_sha256": sha256(SOURCE),
        "source_bytes": SOURCE.stat().st_size,
        "bounds_wgs84": BOUNDS,
        "features_intersecting_bounds": len(features),
        "closest_forest_polygons": summary,
        "output": str(OUTPUT),
        "output_sha256": sha256(OUTPUT),
        "limitation": "Survey of India topographic forest features are map references, not cadastral or current Forest Department demarcation. Distances are planar degrees used only for ranking nearby features.",
    }
    report_path = OUTPUT.with_suffix(".json")
    report_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
