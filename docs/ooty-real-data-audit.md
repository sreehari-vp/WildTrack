# Ooty evidence-based data audit

Status: Phase 1 complete (17 October 2026). The results below define a reproducible research layer for the next implementation phase. They do **not** represent live tracking, an expert-verified species inventory, or legally authoritative boundaries.

## Phase 1 result

The study area is limited to six named Ooty-area regions: Ooty North / Marlimund, Doddabetta, Pykara, Avalanche, Upper Bhavani and Mukurthi. Five extents are the mapped Survey of India reserve-forest features clipped to a 3 km landmark search area; Mukurthi uses the PM GatiShakti 2024 protected-area snapshot. These are documented **WildTrack study extents**. The five clipped extents are not official forest boundary updates, and the Mukurthi snapshot's computed geodesic area is 82.14 km² versus 78.46 km² in its source attribute (4.69% difference); do not use it as a legal boundary without reconciliation.

The retained GBIF query contains **94 source-screened observation candidates across 40 species** (66 birds, 8 mammals, 9 squamates and 11 insects), dated 22 February 2020–20 August 2026. They are direct human observations with species-level identifications, public coordinates, stated positional uncertainty of at most 1 km and explicit Creative Commons licences. Every reported point falls within at least one study extent, while only 49 records have their full uncertainty radius inside an extent; 45 radii cross a boundary. Memberships overlap, with 72 records assigned to Doddabetta and much smaller counts in other extents, so totals by region are not additive and coverage is uneven.

These are **observation events, not 94 individual animals**. There are no verified Ooty telemetry tracks in this package. Species identifications have not received manual expert review. The 79 CC BY-NC records require non-commercial use and attribution; each record's licence and dataset citation are retained. Use the resulting layer for a clearly labelled historical observation view, with uncertainty and source details visible. Do not make it move in the simulator or present it as a current animal position.

Primary outputs: `data/research/phase1-study-regions.geojson`, `data/research/phase1-observation-candidates.json`, and `data/research/phase1-validation-report.json`. The earlier iNaturalist circle screen (143 candidates) and its land-cover cross-tab were exploratory and are superseded for region membership by this final, polygon-based source screen. The final files and reproduction command are described in `data/research/README.md`.

## Land-cover source check

The official [ESA WorldCover 2021 v200 tile](https://esa-worldcover.org/en/data-access) `N09E075` was checked and cropped to a 76.40–76.79 E, 11.18–11.53 N **audit envelope**. The 1.1 MB crop and provenance hashes are in `data/research/ooty-worldcover-2021.tif` and `.json`. The source tile has 11 classes at approximately 10 m resolution, is CC BY 4.0, and has a published global overall accuracy of 76.7%. This is **2021 modelled land cover**, not a legal protected-area boundary, current forest condition, or landslide-risk map. Attribution: © ESA WorldCover project 2021 / Contains modified Copernicus Sentinel data (2021) processed by ESA WorldCover consortium.

The earlier exploratory point-class screen in `scripts/screen_ooty_landcover.py` places 143 provisional iNaturalist candidates at 113 tree-cover pixels, 15 grassland, 10 permanent-water and 5 built-up pixels. It is superseded for region membership by the polygon-based GBIF screen above. A WorldCover class describes the pixel at the reported coordinate only; it does not verify a sighting or create a habitat/hazard zone.

Mukurthi's source-reported area is 78.46 km² ([MoEFCC meeting record](https://moef.gov.in/uploads/2020/12/minutes-of-43rd-meeting.pdf)). The PM GatiShakti snapshot sourced through BharatAtlas includes a Mukurthi polygon, but its geodesic area is approximately 82.14 km², 4.69% above the stated area. It is retained as a **snapshot boundary with unresolved area discrepancy**, not certified as the official park boundary. Reconcile the geometry with a current Forest Department or official notification source before legal or operational use.

## First source-file check

The Nature Conservation Foundation Darwin Core source archive is saved at `data/raw/dwca-anam-mammals-2023-26-v1.0.zip` (SHA-256 `037715C3CA77190BCA3335CEFB37426542D3D0E196CB378FCE1881491F12ADC7`). It contains 4,139 rows. A **temporary rectangular screen** of 76.55–76.78 E, 11.23–11.48 N returns 404 records, but this rectangle is *not* the six-region study boundary. Most screened records cluster around 11.25–11.31 N, 76.73–76.76 E, southeast of the selected forest regions. It would be misleading to call all 404 Ooty forest records.

Using provisional reference points and an 8 km radius solely to test source suitability gives Ooty North 5, Doddabetta 9, Pykara 3, Avalanche 2, Upper Bhavani 0, and Mukurthi 0 records. Circles overlap and these figures must not be summed or used as final zone counts. The archive alone cannot meet the 75–100 target across the six chosen regions. It should be a supplementary source.

The source archive's 404 broad-screen rows have unique occurrence IDs, dates from 26 September 2024 to 28 February 2026, and nonempty coordinate-uncertainty fields. Their `verbatimLocality` is often tea plantation or dry/mixed forest, further reason to filter by actual study polygons. `basisOfRecord=HumanObservation` does not by itself establish whether the record was a direct sighting versus a sign; inspect source fields and notes before labelling it in the UI.

An iNaturalist research-grade species-count query over a *broader* 76.42–76.78 E, 11.20–11.52 N rectangle reported 46 mammal species. This demonstrates potential diversity, but the counts are not yet filtered to the six regions, can include obscured positions, and must not be added to GBIF without deduplication. Query: https://api.inaturalist.org/v1/observations/species_counts?swlat=11.2&swlng=76.42&nelat=11.52&nelng=76.78&quality_grade=research&taxon_id=40151

Additional iNaturalist feasibility screens, centred on **provisional** coordinates with an 8 km radius, returned 47 mammal observations across nine species near Mukurthi and 60 observations across 20 species near Upper Bhavani. A Mukurthi-centred bird screen returned 17 observations across 14 species. These screens overlap and include records with obscured coordinates; they cannot be summed or assigned to final zones. They show a possible supplementary source, not an accepted record count. Queries: https://api.inaturalist.org/v1/observations/species_counts?lat=11.27&lng=76.47&radius=8&quality_grade=research&taxon_id=40151 ; https://api.inaturalist.org/v1/observations/species_counts?lat=11.26&lng=76.53&radius=8&quality_grade=research&taxon_id=40151 ; https://api.inaturalist.org/v1/observations/species_counts?lat=11.27&lng=76.47&radius=8&quality_grade=research&taxon_id=3

The bird screen includes implausible regional matches, which is a warning that obscured/generalized locations and taxon identifications need record-level review. Do not use a species-count result as a vetted occurrence dataset.

### Record-level iNaturalist screen

On 17 October 2026, `scripts/audit_inaturalist.py` retrieved public research-grade, non-captive mammal and bird observations dated 2020 or later within provisional 8 km circles around the six reference points. It saved only IDs, taxon, date, public coordinates, accuracy, privacy, licence and candidate region labels to `data/research/inaturalist-candidates.json` (SHA-256 `09DD0BB10FD9874771BAC1E656A7AAB6FDE56D73DC929D1FD2FEFEF610382CAB`). The 12 circle queries reported 2,104 **unique** records after ID deduplication. The circles overlap and are not approved region boundaries.

A conservative screen kept records with a species-level taxon, observed date, public non-obscured coordinates, stated positional accuracy at most 1 km, and observation licence CC0/CC BY/CC BY-SA. This leaves **143 candidate records across 57 species** (observed 21 December 2020–17 June 2026). Candidate counts by circle are Ooty North 48, Doddabetta 37, Pykara 11, Avalanche 94, Upper Bhavani 1, Mukurthi 1. These counts overlap, are not additive, and will shrink once exact boundaries and habitat rules are applied. The uneven distribution means the project must not promise an equal number of dots in every region.

The 143 are **not yet accepted sightings**: check each against final source-backed boundaries, coordinate uncertainty, observation quality, taxon, duplication with GBIF, and whether a point belongs in the selected habitat rather than nearby settlement. Records for sensitive species with obscured positions are excluded from precise-dot display; they may only support appropriately generalized summaries.

## Scope

The study is limited to six Ooty-area regions: Ooty North, Doddabetta, Pykara, Avalanche, Upper Bhavani, and Mukurthi. Region names are navigation labels. Their study extents must be drawn from documented geography and recorded as WildTrack study boundaries unless an authoritative legal polygon is available. The target is about twelve smaller terrain/use-case zones, subject to actual evidence.

## Current project baseline

| Existing item | Finding | Required treatment |
| --- | --- | --- |
| `managed_areas` | Migration `20260911_0003` inserts four small polygons whose `data_source` is `WildTrack demonstration geometry`. | Replace in a new migration or import job after real source polygons are acquired; never relabel these as official boundaries. |
| `wildlife_observations` | Migration `20260911_0004` inserts six sample positions with synthetic animal tags and relative timestamps. | Keep separate from sourced occurrence data and remove from the evidence-based map before release. |
| Observation schema | Has species, tag, zone, time, confidence, point, and later bitemporal columns; lacks provider record ID, dataset DOI/URL, licence, coordinate uncertainty, geospatial issue flags and evidence type. | Extend before importing third-party records. An occurrence must not be given a fabricated individual animal tag. |
| Map | Supports zone polygons and point records. UI now renders small dots and filters, but the present data are sample records. | Connect only accepted sourced records to the evidence-based layer and show provenance in the selected-record card. |
| Movement | Current tagged sample records can be interpreted as a route. | Do not derive individual movement from GBIF/iNaturalist sightings. Real tracks require linked telemetry and access permission. |

## Source register

| Data | Candidate source | Planned use | Audit gate |
| --- | --- | --- | --- |
| Mukurthi protected-area boundary | Protected Planet WDPCA: https://www.protectedplanet.net/en and official Ministry/Forest Department material | Legal boundary, if a usable polygon is available | Match name, designation, area, geometry and release date; observe WDPCA display/redistribution licence: https://www.unep-wcmc.org/en/wdpa-data-license |
| Forest, grassland, built-up, bare ground and water | ESA WorldCover 2021 10 m: https://esa-worldcover.org/en/data-access | Derive analytical terrain/land-cover zones | Record product/version and attribution. This is land cover, not a legal forest boundary or current-year condition. |
| Height and slope | Copernicus DEM GLO-30: https://portal.opentopography.org/datasetMetadata?otCollectionID=OT.032021.4326.1 | High-elevation and steep-slope zones | Record raster version, vertical datum and resolution; slope is a terrain measure, not a hazard prediction. |
| Landslide susceptibility | Geological Survey of India 1:10,000 Ooty-area maps: https://bhusanket.gsi.gov.in/NLSM_10K_Map.html | Susceptibility overlay only within published coverage | Obtain georeferenced classes or accurately georeference the map; preserve class, scale and publication. Do not generalize beyond coverage. |
| Published wildlife occurrences | GBIF: https://www.gbif.org/occurrence/search | Dated, sourced species observations | Filter to final study polygons; preserve GBIF ID, dataset key/DOI, event date, licence, uncertainty and issues. |
| Candidate mammal dataset | Nature Conservation Foundation via GBIF: https://www.gbif.org/dataset/b219d9b5-ab67-46a2-85b6-278cd7e30f93 (DOI: 10.15468/yv8qss) | Potential mammal records | Published 10 March 2026 under CC BY 4.0. Its metadata lists three contributing groups (4,139, 88 and 32 records) and 47 taxa across several Western Ghats areas. These are **not** Ooty counts or a verified deduplicated total. Filter point-by-point to the final extent. Records include opportunistic sightings and animal signs, so distinguish those evidence types. |
| Individually tracked movements | Movebank: https://www.movebank.org/cms/movebank-content/access-data | Optional real movement layer | Import only a relevant study with explicit access/use rights and stable individual IDs. None confirmed. |

## Proposed zone catalogue

The names below are *analysis concepts*, not verified polygons or legal designations.

| Region | Zone A | Zone B |
| --- | --- | --- |
| Ooty North | Settlement–forest edge | Steep slope, with GSI susceptibility shown separately where mapped |
| Doddabetta | High-elevation ridge | Forest edge |
| Pykara | Water vicinity | Forest habitat |
| Avalanche | Reservoir/stream vicinity | Shola forest |
| Upper Bhavani | Catchment/water vicinity | High-elevation habitat |
| Mukurthi | Montane grassland | Shola forest |

Each final zone requires `region`, `zone_type`, derivation method, data-source URL/version, geometry validity check, area, confidence/limitations, and a short user-facing explanation. Zones may overlap when two conditions apply. No zone is automatically called “dangerous”; susceptibility, terrain and human proximity remain distinct attributes.

## Observation acceptance rules

1. Inside the final study boundary using PostGIS spatial containment; coordinates in WGS84 longitude/latitude order.
2. Species-level identification and a usable event date. Preserve the original taxon and canonical accepted name.
3. Location with documented uncertainty; exclude invalid coordinates, centroids, captive/zoo records and records too imprecise for the intended zone comparison.
4. Stable source ID, source URL, dataset ID/DOI and licence. Deduplicate iNaturalist records that also appear in GBIF.
5. Flag obscured or sensitive locations and generalize public display accordingly. Never imply the visible coordinate is the exact animal position.
6. Select a diverse 75–100 **observations**, aiming for roughly 8–12 species across taxonomic groups if supported by local data. Do not manufacture quotas, animals, timestamps or movement paths to hit the target.
7. Show observation date and source in the UI. “Live” is reserved for an actual live feed; “tracked animal” is reserved for linked individual telemetry.

## Phase 1 exit checks

- [x] Existing sample zones and records identified in code.
- [x] Public source snapshots and per-record licences/citations retained.
- [x] Six named Ooty study extents created and their derivation documented; boundary limitations recorded.
- [x] Dated, species-level, public-coordinate GBIF candidates filtered against the study extents.
- [x] Counts, taxonomic diversity, licences, coordinate-uncertainty flags and source hashes recorded in the validation report.
- [x] Confirmed the 94 records are observation events, not a unique animal census or movement tracks.
- [x] Confirmed no Ooty-specific public telemetry source is included or verified for this project.
- [x] Earlier provisional candidate screens marked as superseded.

Phase 1 is complete as a **research-data and boundary baseline**. The 94 candidates are sufficient to start Phase 2 schema and import work, but not to claim 75–100 individually identified or tracked animals. Phase 2 must derive and document the thematic zones from land-cover, elevation, water and hazard sources, then implement provenance-aware observation storage and display. Reconcile Mukurthi's polygon area discrepancy before treating its outline as authoritative.
