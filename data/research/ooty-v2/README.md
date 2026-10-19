# Ooty forest dataset V2 — candidate package

This package is **additive**. It does not replace the existing database or the
Phase 1/2 files. The original Desktop project imported this version after archiving its previous database state. Earlier records remain available through the API.

## Geography

`study-regions.geojson` has eight named forest analysis extents: Wenlock Downs,
Naduvattam, Porthimund, Kundah, Mukurthi Lake, Nilgiri Peak, Doddabetta and
Kalhatty. They are drawn from the retained Survey of India forest extract via
BharatAtlas, deduplicated and clipped to the local ESA WorldCover 2021 raster
footprint. Source names, source URL, licence note and hash are recorded on each
feature. These are **not certified legal boundaries**. The earlier six study
extents remain available in the original files.

`landcover-zones.geojson` contains 30 modelled land-cover classes inside those
extents. Each zone links to one forest region and carries the ESA WorldCover
source, DOI, resolution and derivation parameters. Display geometry omits
components below 5,000 m² and simplifies by about 20 m. Tree and grassland
zones are used as scenario habitat contexts; built-up, cropland, sparse cover
and water remain map context. Land cover does not prove risk, elevation, habitat
suitability, or wildlife presence.

## Wildlife evidence and scenario

`gbif-mammal-search.json` is a fresh GBIF Mammalia API snapshot of 1,325 records
in the local 76.4–76.79° E, 11.18–11.53° N envelope. It records the exact query
URLs and retrieval time. `mammal-observation-candidates.json` holds 35 records
that pass the saved quality/licence screen, exclude selected domestic species
and the roadkill dataset, and intersect the eight forest polygons. There are
13 distinct species; three regions have no accepted records. The excluded
roadkill dataset is a mortality-event source, not evidence of living tracked
animals. These are historical candidate sightings, not unique animals or telemetry.
`gbif-datasets.json` retains attribution metadata for the three included datasets.
Do not fabricate sightings to make region counts even.

`simulated-mammals.json` is separate: 75 synthetic tracker identities across
16 regionally referenced mammal species, balanced at 9–10 per forest region.
Starting points and short local routes lie inside tree or grassland zone
geometries. The species checklist is regional context only; placement does not
assert a real sighting or local population abundance. Seven of the 75 scenario
trackers are Asian elephants. Generated IDs use the `SIM-V2-` prefix.

## Rebuild

From the workspace root, with the backend virtual environment:

```powershell
backend\venv\Scripts\python.exe scripts\build_ooty_v2_regions.py
backend\venv\Scripts\python.exe scripts\derive_ooty_v2_landcover_zones.py --regions data/research/ooty-v2/study-regions.geojson --output data/research/ooty-v2/landcover-zones.geojson --minimum-component-area-m2 5000 --simplification-tolerance-degrees 0.0002
backend\venv\Scripts\python.exe scripts\fetch_ooty_v2_mammals.py
backend\venv\Scripts\python.exe scripts\screen_ooty_v2_mammals.py
backend\venv\Scripts\python.exe scripts\fetch_ooty_v2_datasets.py
backend\venv\Scripts\python.exe scripts\build_ooty_v2_simulation.py
```

GBIF and ESA WorldCover provide occurrence and land-cover data respectively:
https://techdocs.gbif.org/en/openapi/v1/occurrence and
https://esa-worldcover.org/en/data-access. The source forest URL is recorded in
`../nilgiris-soi-forest-features.json`.
