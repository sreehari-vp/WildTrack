"""Extract the Mukurthi National Park record from the GatiShakti PA layer."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import duckdb
from shapely import from_wkb
from shapely.geometry import mapping

SOURCE = Path("data/raw/protected-areas-temporary.parquet")
OUTPUT = Path("data/research/mukurthi-national-park-gatishakti.geojson")


def main() -> None:
    rows = duckdb.connect().execute(
        "SELECT * EXCLUDE(geometry), geometry FROM read_parquet(?) "
        "WHERE lower(name) LIKE '%mukurthi%' OR lower(pa_name) LIKE '%mukurthi%'",
        [str(SOURCE)],
    ).fetchall()
    columns = [
        "id", "gid", "name", "state", "district", "circle", "division", "category",
        "source", "notif_no", "notif_dat", "notif_year", "zone", "area_ha", "st_2011",
        "dt_2011", "code", "pa_name", "esta_year", "area_sqkm", "category1", "habitat",
        "biogr_zone", "animals", "plants", "best_time", "by_air", "by_rail", "by_road",
        "by_sea", "stay", "address", "contact", "georss", "geometry",
    ]
    features = []
    for row in rows:
        values = dict(zip(columns, row, strict=True))
        geometry = from_wkb(values.pop("geometry"))
        properties = {key: value for key, value in values.items() if value is not None}
        features.append({"type": "Feature", "geometry": mapping(geometry), "properties": properties})
    if not features:
        raise SystemExit("No Mukurthi record found in the protected-area source")
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(json.dumps({"type": "FeatureCollection", "features": features}, separators=(",", ":")), encoding="utf-8")
    digest = hashlib.sha256(OUTPUT.read_bytes()).hexdigest()
    report = {
        "source_url": "https://pub-0429b8e3b5a946e69ea007df844a6f1c.r2.dev/environment/forests/GatiShakti_Wildlife_Sanctuaries_and_National_Parks.parquet",
        "publisher": "BharatAtlas; attributed source PM GatiShakti",
        "licence": "CC0-1.0 as stated by BharatAtlas",
        "feature_count": len(features),
        "records": [{key: feature["properties"].get(key) for key in ("id", "name", "state", "district", "category", "source", "area_sqkm", "area_ha", "animals")} for feature in features],
        "output": str(OUTPUT),
        "output_sha256": digest,
        "limitations": "Snapshot boundary for display/research; verify official notification geometry before legal, cadastral or enforcement use. Source field and stated area retained verbatim.",
    }
    OUTPUT.with_suffix(".json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
