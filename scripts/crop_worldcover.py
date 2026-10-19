"""Crop the published ESA WorldCover 2021 tile to the Ooty audit envelope.

This is a land-cover reference raster, not an official forest or study boundary.
Run with a locally downloaded N09E075 source tile; do not commit the 76 MB tile.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter
from pathlib import Path

import rasterio
from rasterio.windows import from_bounds, transform

BOUNDS = (76.40, 11.18, 76.79, 11.53)  # west, south, east, north; audit envelope
SOURCE_URL = (
    "https://esa-worldcover.s3.eu-central-1.amazonaws.com/v200/2021/map/"
    "ESA_WorldCover_10m_2021_v200_N09E075_Map.tif"
)
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


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as file:
        for block in iter(lambda: file.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("source", type=Path, help="Downloaded official N09E075 GeoTIFF")
    parser.add_argument("--output", type=Path, default=Path("data/research/ooty-worldcover-2021.tif"))
    args = parser.parse_args()
    args.output.parent.mkdir(parents=True, exist_ok=True)

    with rasterio.open(args.source) as src:
        if src.crs.to_epsg() != 4326 or src.count != 1:
            raise ValueError("Unexpected WorldCover tile CRS or band count")
        window = from_bounds(*BOUNDS, transform=src.transform).round_offsets().round_lengths()
        values = src.read(1, window=window)
        profile = src.profile.copy()
        profile.update(
            width=values.shape[1],
            height=values.shape[0],
            transform=transform(window, src.transform),
            compress="deflate",
            tiled=True,
        )
        with rasterio.open(args.output, "w", **profile) as dst:
            dst.write(values, 1)
            dst.update_tags(
                source=SOURCE_URL,
                product="ESA WorldCover 10m 2021 v200",
                note="Audit envelope crop; not a legal boundary or hazard layer",
            )

    counts = Counter(int(value) for value in values.flat)
    metadata = {
        "source_url": SOURCE_URL,
        "source_sha256": sha256(args.source),
        "crop_sha256": sha256(args.output),
        "bounds_requested_wgs84": BOUNDS,
        "product": "ESA WorldCover 10m 2021 v200",
        "doi": "10.5281/zenodo.7254221",
        "licence": "CC BY 4.0",
        "class_pixel_counts": {CLASSES.get(code, str(code)): count for code, count in sorted(counts.items())},
        "limitation": "2021 modelled land cover, not a legal forest boundary or current condition",
    }
    metadata_path = args.output.with_suffix(".json")
    metadata_path.write_text(json.dumps(metadata, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"raster": str(args.output), "metadata": str(metadata_path), "pixels": values.size, "classes": metadata["class_pixel_counts"]}, indent=2))


if __name__ == "__main__":
    main()
