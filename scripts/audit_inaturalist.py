"""Screen public iNaturalist observations around provisional Ooty reference points.

This is a source audit, not a WildTrack import. The 8 km circles are deliberately
temporary and must not be used as final region or zone boundaries.
"""

from __future__ import annotations

import json
import time
from urllib.error import URLError
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import Request, urlopen

API = "https://api.inaturalist.org/v1/observations"
REGIONS = {
    "ooty_north": (11.43, 76.70),
    "doddabetta": (11.40069, 76.73568),
    "pykara": (11.49031, 76.59106),
    "avalanche": (11.322, 76.611),
    "upper_bhavani": (11.23, 76.52),
    "mukurthi": (11.27, 76.50),
}
TAXA = {"mammals": 40151, "birds": 3}
OUTPUT = Path("data/research/inaturalist-candidates.json")


def fetch(params: dict[str, str | int | float]) -> dict:
    request = Request(
        API + "?" + urlencode(params),
        headers={"User-Agent": "WildTrack academic source audit (read-only)"},
    )
    last_error: Exception | None = None
    for attempt in range(5):
        try:
            with urlopen(request, timeout=60) as response:
                return json.load(response)
        except (TimeoutError, URLError) as error:
            last_error = error
            if attempt == 4:
                break
            time.sleep(2**attempt)
    raise RuntimeError(f"iNaturalist request failed after 5 attempts: {last_error}")


def main() -> None:
    records: dict[int, dict] = {}
    screens: list[dict] = []
    for region, (lat, lng) in REGIONS.items():
        for group, taxon_id in TAXA.items():
            params = {
                "lat": lat,
                "lng": lng,
                "radius": 8,
                "taxon_id": taxon_id,
                "quality_grade": "research",
                "captive": "false",
                "d1": "2020-01-01",
                "per_page": 200,
                "page": 1,
            }
            first = fetch(params)
            total = int(first["total_results"])
            pages = (total + 199) // 200
            screens.append({"region": region, "group": group, "reported_count": total})
            for page in range(1, pages + 1):
                data = first if page == 1 else fetch({**params, "page": page})
                for item in data["results"]:
                    taxon = item.get("taxon") or {}
                    entry = records.setdefault(
                        item["id"],
                        {
                            "id": item["id"],
                            "source_url": f"https://www.inaturalist.org/observations/{item['id']}",
                            "taxon_id": taxon.get("id"),
                            "scientific_name": taxon.get("name"),
                            "taxon_rank": taxon.get("rank"),
                            "observed_on": item.get("observed_on"),
                            "location": item.get("location"),
                            "positional_accuracy_m": item.get("positional_accuracy"),
                            "geoprivacy": item.get("geoprivacy"),
                            "obscured": item.get("obscured"),
                            "license_code": item.get("license_code"),
                            "quality_grade": item.get("quality_grade"),
                            "captive": item.get("captive"),
                            "candidate_regions": [],
                        },
                    )
                    if region not in entry["candidate_regions"]:
                        entry["candidate_regions"].append(region)
                if page < pages:
                    time.sleep(0.5)
            print(f"{region}: {group} {total}")
            time.sleep(0.5)

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(
        json.dumps(
            {
                "method": "Public iNaturalist API; 8 km discovery radius around named Ooty-area reference points, research grade, wild, observed from 2020. Circles overlap and are not study boundaries.",
                "reference_points": {
                    "ooty_north": {"lat": 11.43, "lng": 76.70, "source": "Marlimund Reserved Forest map reference; not a legal boundary"},
                    "doddabetta": {"lat": 11.40069, "lng": 76.73568, "source": "https://mapcarta.com/14890628"},
                    "pykara": {"lat": 11.49031, "lng": 76.59106, "source": "https://mapcarta.com/35266622"},
                    "avalanche": {"lat": 11.322, "lng": 76.611, "source": "https://www.wikidata.org/wiki/Q4827484"},
                    "upper_bhavani": {"lat": 11.23, "lng": 76.52, "source": "https://wgbis.ces.iisc.ac.in/biodiversity/sahyadri_enews/newsletter/Issue85/article.html"},
                    "mukurthi": {"lat": 11.27, "lng": 76.50, "source": "Approximate park-interior reference; park extent: https://www.ecoinfoindia.org/lldb_mukurthi_np.html"},
                },
                "screens": screens,
                "records": sorted(records.values(), key=lambda item: item["id"]),
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    print(f"unique candidates: {len(records)} -> {OUTPUT}")


if __name__ == "__main__":
    main()
