"""Fetch a bounded GBIF occurrence search for final local spatial screening."""

from __future__ import annotations

import hashlib
import json
import time
from datetime import UTC, datetime
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

API = "https://api.gbif.org/v1/occurrence/search"
BOUNDS = (76.35, 11.15, 76.90, 11.57)
LIMIT = 300
OUTPUT = Path("data/research/gbif-ooty-search.json")
QUERY = {
    "country": "IN",
    "kingdomKey": 1,
    "geometry": "POLYGON((76.35 11.15,76.9 11.15,76.9 11.57,76.35 11.57,76.35 11.15))",
    "hasCoordinate": "true",
    "year": "2020,2026",
    "taxonRank": "SPECIES",
    "coordinateUncertaintyInMeters": "0,1000",
    "basisOfRecord": "HUMAN_OBSERVATION",
    "limit": LIMIT,
}
FIELDS = (
    "key", "datasetKey", "datasetTitle", "publishingOrgKey", "species", "scientificName",
    "taxonKey", "taxonRank", "kingdom", "phylum", "class", "order", "family", "genus",
    "eventDate", "year", "month", "day", "decimalLatitude", "decimalLongitude",
    "coordinateUncertaintyInMeters", "basisOfRecord", "occurrenceStatus", "license",
    "occurrenceID", "references", "issues", "establishmentMeans", "degreeOfEstablishment",
    "informationWithheld", "dataGeneralizations", "georeferenceRemarks", "sensitivityStatus",
)


def fetch_page(offset: int) -> dict:
    query = urlencode({**QUERY, "offset": offset})
    request = Request(API + "?" + query, headers={"User-Agent": "WildTrack academic occurrence audit/1.0"})
    last_error: Exception | None = None
    for attempt in range(5):
        try:
            with urlopen(request, timeout=60) as response:
                return json.load(response)
        except (TimeoutError, URLError, HTTPError) as error:
            last_error = error
            if attempt < 4:
                time.sleep(2**attempt)
    raise RuntimeError(f"GBIF page offset={offset} failed after retries: {last_error}")


def main() -> None:
    first = fetch_page(0)
    total = int(first["count"])
    records: dict[int, dict] = {}
    for offset in range(0, min(total, 100_000), LIMIT):
        page = first if offset == 0 else fetch_page(offset)
        for item in page.get("results", []):
            key = item.get("key")
            if key is None:
                continue
            records[int(key)] = {name: item.get(name) for name in FIELDS if item.get(name) is not None}
        print(f"retrieved {min(offset + LIMIT, total)} / {total}", flush=True)
        time.sleep(0.25)
    document = {
        "retrieved_at_utc": datetime.now(UTC).isoformat(),
        "api": API,
        "query": QUERY,
        "query_bounds_wgs84": BOUNDS,
        "reported_result_count": total,
        "record_count_downloaded": len(records),
        "record_fields": list(FIELDS),
        "records": sorted(records.values(), key=lambda row: row["key"]),
    }
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(json.dumps(document, separators=(",", ":")), encoding="utf-8")
    digest = hashlib.sha256(OUTPUT.read_bytes()).hexdigest()
    print(json.dumps({"file": str(OUTPUT), "count": len(records), "sha256": digest}))


if __name__ == "__main__":
    main()
