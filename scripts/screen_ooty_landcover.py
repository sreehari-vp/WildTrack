"""Cross-tab provisional iNaturalist candidates against 2021 land cover.

The class at a reported point is an audit clue, not a validated habitat assignment:
coordinate uncertainty and WorldCover classification error still apply.
"""

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

import rasterio

CANDIDATES = Path("data/research/inaturalist-candidates.json")
RASTER = Path("data/research/ooty-worldcover-2021.tif")
REPORT = Path("data/research/ooty-landcover-screen.json")
CLASSES = {
    10: "Tree cover",
    20: "Shrubland",
    30: "Grassland",
    40: "Cropland",
    50: "Built-up",
    60: "Bare/sparse vegetation",
    70: "Snow and ice",
    80: "Permanent water bodies",
    90: "Herbaceous wetland",
    95: "Mangroves",
    100: "Moss and lichen",
}


def accepted_for_screen(record: dict) -> bool:
    try:
        return (
            record["taxon_rank"] == "species"
            and bool(record["observed_on"])
            and bool(record["location"])
            and not record["obscured"]
            and record["geoprivacy"] in (None, "open")
            and 0 <= float(record["positional_accuracy_m"]) <= 1000
            and record["license_code"] in ("cc0", "cc-by", "cc-by-sa")
        )
    except (KeyError, TypeError, ValueError):
        return False


def main() -> None:
    candidates = json.loads(CANDIDATES.read_text(encoding="utf-8"))["records"]
    screened = [record for record in candidates if accepted_for_screen(record)]
    counts: Counter[str] = Counter()
    by_region: dict[str, Counter[str]] = {}
    outside = 0
    with rasterio.open(RASTER) as raster:
        for record in screened:
            lat, lon = (float(value) for value in record["location"].split(","))
            if not (raster.bounds.left <= lon < raster.bounds.right and raster.bounds.bottom <= lat < raster.bounds.top):
                outside += 1
                continue
            value = int(next(raster.sample([(lon, lat)]))[0])
            label = CLASSES.get(value, f"Unknown ({value})")
            counts[label] += 1
            for region in record["candidate_regions"]:
                by_region.setdefault(region, Counter())[label] += 1

    report = {
        "screened_candidates": len(screened),
        "inside_raster": len(screened) - outside,
        "outside_raster": outside,
        "class_at_reported_point": dict(sorted(counts.items())),
        "by_overlapping_provisional_circle": {
            region: dict(sorted(classes.items())) for region, classes in sorted(by_region.items())
        },
        "interpretation": "Exploratory 2021 land-cover screen only; circles overlap. No study polygon, current habitat, or point accuracy validation is implied.",
    }
    REPORT.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
