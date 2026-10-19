"""Fetch GBIF dataset attribution for screened Ooty V2 mammal records."""

from __future__ import annotations

import json
from pathlib import Path
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
DIRECTORY = ROOT / "data/research/ooty-v2"


def main() -> None:
    rows = json.loads((DIRECTORY / "mammal-observation-candidates.json").read_text(encoding="utf-8"))
    keys = sorted({row["dataset_key"] for row in rows})
    datasets = []
    for key in keys:
        url = f"https://api.gbif.org/v1/dataset/{key}"
        request = Request(url, headers={"User-Agent": "WildTrack/1.0 (academic Ooty biodiversity research)"})
        with urlopen(request, timeout=30) as response:
            item = json.load(response)
        datasets.append({
            "key": key,
            "title": item.get("title"),
            "doi": item.get("doi"),
            "license": item.get("license"),
            "citation": item.get("citation"),
            "publishingOrganizationTitle": item.get("publishingOrganizationTitle"),
            "source_url": url,
        })
    path = DIRECTORY / "gbif-datasets.json"
    path.write_text(json.dumps({"datasets": datasets}, indent=2) + "\n", encoding="utf-8")
    print(f"Saved attribution for {len(datasets)} GBIF datasets")


if __name__ == "__main__":
    main()
