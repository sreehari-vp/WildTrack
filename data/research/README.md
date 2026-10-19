# WildTrack Ooty Phase 1 research package

**Phase 1 is complete.** This folder contains source snapshots and reproducible outputs for six Ooty-area study regions. The regions are analysis extents, not legal forest or park demarcations. The occurrence output is a screened research candidate layer, not telemetry or a verified inventory of resident animals.

## Primary Phase 1 outputs

- `phase1-study-regions.geojson` — five WildTrack study areas made by clipping Survey of India reserve-forest features to 3 km around named landmarks, plus a 2024 Mukurthi National Park snapshot polygon from PM GatiShakti. The Mukurthi source reports 78.46 km²; its supplied geometry measures about 82.14 km² geodesically (4.69% difference). Verify that boundary before operational use.
- `phase1-observation-candidates.json` — 94 source-screened GBIF occurrence records across 40 species. All are species-level, dated, direct human observations with public coordinates, stated uncertainty no greater than 1 km, and an explicit Creative Commons licence. The reported coordinate is inside a study extent for all 94; the full uncertainty radius is contained for 49 and crosses a region edge for 45. Region memberships overlap, so per-region totals are not additive.
- `phase1-validation-report.json` — machine-readable counts, sources, hashes, boundary areas, selection criteria, checks and limitations.
- `phase2-landcover-zones.geojson` — reproducible WorldCover 2021 categories clipped to the six study extents. It contains tree cover, grassland, water/wetland, built-up footprint, cultivated land, and bare/sparse cover overlays.
- `gbif-ooty-search.json` and `gbif-dataset-metadata.json` — retained GBIF API response and dataset metadata used to reproduce the screen.
- `nilgiris-soi-forest-features.geojson` and `mukurthi-national-park-gatishakti.geojson` — clipped source feature extracts used to build study extents. They are cartographic snapshots, not cadastral/legal boundaries.
- `ooty-worldcover-2021.tif` plus `ooty-worldcover-2021.json` — small ESA WorldCover 2021 v200 land-cover crop and provenance. It is a 2021 modelled land-cover product, not a current hazard map or official forest classification.

## Use and attribution

The occurrence records retain their source IDs, dataset citation/DOI, source URL, event date, licence and location uncertainty. The final screen uses iNaturalist Research-grade Observations and Observation.org datasets. **79 of the 94 records are CC BY-NC 4.0**, so those records may only be reused non-commercially and require attribution; preserve each row's licence when importing or displaying it. The remaining records are CC BY 4.0 (13) or CC0 (2). Do not strip source credits or imply the observations identify tagged individuals.

The NCF Darwin Core archive was a separate source check; it is not added to the 94 records. `inaturalist-candidates.json`, `ncf-phase1-*`, and `ooty-landcover-screen.json` are earlier exploratory screens superseded for region membership by the Phase 1 outputs above. Do not import those older screens.

The six region labels are Ooty North / Marlimund, Doddabetta, Pykara, Avalanche, Upper Bhavani and Mukurthi. Five study extents use selected mapped reserve-forest polygons clipped to a 3 km landmark search area; Mukurthi uses the cited 2024 snapshot. These study areas may overlap. The saved raster crop covers all six current study geometries (100% coverage recorded in each derived feature), while the WorldCover product remains a 2021 modelled layer. Land-cover overlays do not claim elevation, slope, rocky ground, waterfall, landslide susceptibility, danger, or habitat suitability. No GSI susceptibility layer or terrain DEM is included yet.

No movement paths or live animal locations can be inferred from this occurrence data. A visible point is a reported observation coordinate with uncertainty, not the animal's exact current location. Manual taxonomic expert review has not been done.

## Reproduction

From the repository root, with the research dependencies installed in `backend/venv`:

```powershell
backend\venv\Scripts\python.exe -m pip install -r scripts\requirements-research.txt
backend\venv\Scripts\python.exe scripts\finalize_phase1_dataset.py --forest-selection-radius-m 3000
backend\venv\Scripts\python.exe scripts\derive_phase2_landcover_zones.py
```

The Phase 1 script reads the retained source snapshots and rewrites its outputs. The Phase 2 zone derivation and database import commands are in the repository README; database import runs in dry-run mode unless `--apply` is passed, and requires Alembic migration `0006_research_evidence` first.
