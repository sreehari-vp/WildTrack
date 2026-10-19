"""Fetch a reproducible GBIF mammal candidate snapshot for the Ooty V2 area.

This is read-only against GBIF and writes only new versioned files. Records are
screened again against the saved forest polygons before any use in WildTrack.
"""

from __future__ import annotations

import json
import time
from datetime import UTC, datetime
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "data/research/ooty-v2/gbif-mammal-search.json"
API = "https://api.gbif.org/v1/occurrence/search"
PARAMS = {
    "taxonKey": "359",  # GBIF Mammalia
    "hasCoordinate": "true",
    "country": "IN",
    "decimalLatitude": "11.18,11.53",
    "decimalLongitude": "76.4,76.79",
    "limit": "300",
}


def main() -> None:
    records = []
    urls = []
    count = None
    for offset in range(0, 30_000, 300):
        url = f"{API}?{urlencode({**PARAMS, 'offset': str(offset)})}"
        request = Request(url, headers={"User-Agent": "WildTrack/1.0 (academic Ooty biodiversity research)"})
        with urlopen(request, timeout=30) as response:
            page = json.load(response)
        urls.append(url)
        count = int(page["count"])
        records.extend(page["results"])
        if page["endOfRecords"] or len(records) >= count:
            break
        time.sleep(0.2)
    else:
        raise RuntimeError("GBIF page safety limit reached; snapshot not written")

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(json.dumps({
        "source": "GBIF occurrence search API",
        "retrieved_at": datetime.now(UTC).isoformat(),
        "query": PARAMS,
        "reported_count": count,
        "page_urls": urls,
        "records": records,
    }, separators=(",", ":")) + "\n", encoding="utf-8")
    print(json.dumps({"reported_count": count, "downloaded": len(records), "pages": len(urls), "output": str(OUTPUT)}, indent=2))


if __name__ == "__main__":
    main()
