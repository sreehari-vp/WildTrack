"""Resolve GBIF dataset keys used by the bounded Ooty occurrence search."""

from __future__ import annotations

import json
import time
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

INPUT = Path("data/research/gbif-ooty-search.json")
OUTPUT = Path("data/research/gbif-dataset-metadata.json")
FIELDS = ("key", "title", "description", "type", "doi", "license", "citation", "pubDate", "publisher")


def main() -> None:
    raw = json.loads(INPUT.read_text(encoding="utf-8"))
    keys = sorted({row["datasetKey"] for row in raw["records"] if row.get("datasetKey")})
    datasets = []
    for key in keys:
        request = Request(f"https://api.gbif.org/v1/dataset/{key}", headers={"User-Agent": "WildTrack academic source audit/1.0"})
        error = None
        for attempt in range(5):
            try:
                with urlopen(request, timeout=60) as response:
                    item = json.load(response)
                datasets.append({field: item.get(field) for field in FIELDS if item.get(field) is not None})
                print(f"resolved {key}: {item.get('title')}", flush=True)
                break
            except (TimeoutError, URLError, HTTPError) as exc:
                error = exc
                if attempt < 4:
                    time.sleep(2**attempt)
        else:
            datasets.append({"key": key, "error": str(error)})
        time.sleep(0.2)
    OUTPUT.write_text(json.dumps({"api": "https://api.gbif.org/v1/dataset/{datasetKey}", "datasets": datasets}, indent=2) + "\n", encoding="utf-8")
    print(f"saved {len(datasets)} dataset records to {OUTPUT}")


if __name__ == "__main__":
    main()
