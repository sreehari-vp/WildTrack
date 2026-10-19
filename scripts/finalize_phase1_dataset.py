"""Build an auditable Phase 1 boundary and occurrence validation report.

Five named focus areas clip Survey of India reserve-forest polygons to a small
search area around a documented landmark. Mukurthi uses its protected-area polygon.
"""

from __future__ import annotations

import hashlib
import json
import math
import argparse
from collections import Counter
from pathlib import Path

import rasterio
from pyproj import Geod
from shapely.geometry import Point, mapping, shape
from shapely.ops import transform, unary_union

FORESTS = Path("data/research/nilgiris-soi-forest-features.geojson")
MUKURTHI = Path("data/research/mukurthi-national-park-gatishakti.geojson")
OCCURRENCES = Path("data/research/gbif-ooty-search.json")
DATASET_METADATA = Path("data/research/gbif-dataset-metadata.json")
WORLD_COVER = Path("data/research/ooty-worldcover-2021.tif")
REGIONS = {
    "ooty_north": {"label": "Ooty North / Marlimund", "lat": 11.43, "lon": 76.70, "radius_m": 0},
    "doddabetta": {"label": "Doddabetta", "lat": 11.40069, "lon": 76.73568, "radius_m": 0},
    "pykara": {"label": "Pykara", "lat": 11.49031, "lon": 76.59106, "radius_m": 0},
    "avalanche": {"label": "Avalanche", "lat": 11.322, "lon": 76.611, "radius_m": 0},
    "upper_bhavani": {"label": "Upper Bhavani", "lat": 11.23, "lon": 76.52, "radius_m": 0},
    "mukurthi": {"label": "Mukurthi National Park", "lat": 11.27, "lon": 76.50, "radius_m": 0},
}
M_PER_DEGREE = 111_320
LAT0 = 11.35
LON_SCALE = math.cos(math.radians(LAT0))
WORLD_CLASSES = {
    10: "Tree cover", 20: "Shrubland", 30: "Grassland", 40: "Cropland",
    50: "Built-up", 60: "Bare/sparse vegetation", 70: "Snow and ice",
    80: "Permanent water bodies", 90: "Herbaceous wetland", 95: "Mangroves", 100: "Moss and lichen",
}


def to_local(x: float, y: float, z: float | None = None):
    return (x * M_PER_DEGREE * LON_SCALE, y * M_PER_DEGREE)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as file:
        for block in iter(lambda: file.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def valid_candidate(record: dict) -> bool:
    try:
        license_uri = str(record.get("license", "")).lower()
        license_ok = any(token in license_uri for token in (
            "creativecommons.org/publicdomain/zero/1.0",
            "creativecommons.org/licenses/by/4.0",
            "creativecommons.org/licenses/by-sa/4.0",
            "creativecommons.org/licenses/by-nc/4.0",
            "cc0-1.0", "cc-by-4.0", "cc-by-sa-4.0",
        ))
        bad_coordinate_issues = {
            "COORDINATE_INVALID", "COUNTRY_COORDINATE_MISMATCH", "ZERO_COORDINATE",
            "COORDINATE_OUT_OF_RANGE", "COORDINATE_UNCERTAINTY_METERS_INVALID",
        }
        return (
            str(record.get("taxonRank", "")).upper() == "SPECIES"
            and bool(record.get("eventDate"))
            and record.get("occurrenceStatus", "PRESENT") == "PRESENT"
            and record.get("basisOfRecord") == "HUMAN_OBSERVATION"
            and record.get("decimalLatitude") is not None
            and record.get("decimalLongitude") is not None
            and record.get("coordinateUncertaintyInMeters") is not None
            and 0 <= float(record["coordinateUncertaintyInMeters"]) <= 1000
            and license_ok
            and not bad_coordinate_issues.intersection(record.get("issues", []))
            and not record.get("informationWithheld")
            and not record.get("dataGeneralizations")
            and str(record.get("sensitivityStatus", "")).lower() not in {"sensitive", "restricted"}
            and str(record.get("establishmentMeans", "")).upper() not in {"CAPTIVE", "CULTIVATED"}
        )
    except (KeyError, TypeError, ValueError):
        return False


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--forest-selection-radius-m", type=int, default=3000)
    args = parser.parse_args()
    if args.forest_selection_radius_m < 0:
        raise SystemExit("Radius must not be negative")
    for code in REGIONS:
        if code != "mukurthi":
            REGIONS[code]["radius_m"] = args.forest_selection_radius_m

    forest_features = json.loads(FORESTS.read_text(encoding="utf-8"))["features"]
    reserve_blocks = []
    seen_forest_geometries: set[bytes] = set()
    for feature in forest_features:
        props = feature["properties"]
        if str(props.get("type", "")).strip().upper() != "RESERVED":
            continue
        geometry = shape(feature["geometry"])
        if not geometry.is_valid:
            geometry = geometry.buffer(0)
        geometry_key = geometry.normalize().wkb
        if geometry_key in seen_forest_geometries:
            continue
        seen_forest_geometries.add(geometry_key)
        reserve_blocks.append((props, transform(to_local, geometry)))

    region_geometries = {}
    region_sources = {}
    for code, region in REGIONS.items():
        if code == "mukurthi":
            pa_features = json.loads(MUKURTHI.read_text(encoding="utf-8"))["features"]
            region_geometries[code] = unary_union([transform(to_local, shape(f["geometry"])) for f in pa_features])
            region_sources[code] = [{"name": "Mukurthi National Park", "source": "PM GatiShakti snapshot 2024"}]
            continue
        x, y = to_local(region["lon"], region["lat"])
        discovery = Point(x, y).buffer(region["radius_m"])
        selected = [(props, geometry.intersection(discovery)) for props, geometry in reserve_blocks if geometry.intersects(discovery)]
        selected = [(props, geometry) for props, geometry in selected if not geometry.is_empty and geometry.area > 0]
        region_geometries[code] = unary_union([geometry for _, geometry in selected]) if selected else Point(x, y).buffer(0)
        region_sources[code] = [
            {"name": str(props.get("name", "")).strip() or "Unnamed reserved forest feature", "source_area_m2": props.get("source_area_m2"), "study_clip_area_m2": round(geometry.area, 2), "source_id": props.get("unique_id")}
            for props, geometry in selected
        ]

    candidate_doc = json.loads(OCCURRENCES.read_text(encoding="utf-8"))
    candidates = [record for record in candidate_doc["records"] if valid_candidate(record)]
    dataset_doc = json.loads(DATASET_METADATA.read_text(encoding="utf-8"))
    datasets = {item["key"]: item for item in dataset_doc["datasets"] if item.get("key")}
    seen: set[int] = set()
    seen_occurrence_ids: set[str] = set()
    accepted: list[dict] = []
    screening_counts: Counter[str] = Counter()
    landcover_counts: Counter[str] = Counter()
    with rasterio.open(WORLD_COVER) as cover:
        for record in candidates:
            record_id = int(record["key"])
            if record_id in seen:
                screening_counts["duplicate_source_id_excluded"] += 1
                continue
            seen.add(record_id)
            source_occurrence_id = str(record.get("occurrenceID", "")).strip()
            if source_occurrence_id and source_occurrence_id in seen_occurrence_ids:
                screening_counts["duplicate_occurrence_id_excluded"] += 1
                continue
            if source_occurrence_id:
                seen_occurrence_ids.add(source_occurrence_id)
            lat = float(record["decimalLatitude"])
            lon = float(record["decimalLongitude"])
            x, y = to_local(lon, lat)
            point = Point(x, y)
            accuracy_m = float(record["coordinateUncertaintyInMeters"])
            uncertainty = point.buffer(accuracy_m)
            memberships = [code for code, geometry in region_geometries.items() if geometry.covers(point)]
            if not memberships:
                screening_counts["outside_study_extent_excluded"] += 1
                continue
            if not any(region_geometries[code].covers(uncertainty) for code in memberships):
                screening_counts["uncertainty_crosses_region_edge_flagged"] += 1
            class_value = int(next(cover.sample([(lon, lat)]))[0])
            land_class = WORLD_CLASSES.get(class_value, f"Unknown {class_value}")
            landcover_counts[land_class] += 1
            dataset = datasets.get(record.get("datasetKey"), {})
            accepted.append({
                "source": "GBIF occurrence search",
                "source_id": record_id,
                "dataset_key": record.get("datasetKey"),
                "dataset_title": dataset.get("title") or record.get("datasetTitle"),
                "dataset_doi": dataset.get("doi"),
                "dataset_citation": (dataset.get("citation") or {}).get("text"),
                "source_url": f"https://www.gbif.org/occurrence/{record_id}",
                "original_occurrence_id": record.get("occurrenceID"),
                "species": record.get("species") or record.get("scientificName"),
                "taxon_id": record.get("taxonKey"),
                "class": record.get("class"),
                "observed_on": record["eventDate"],
                "latitude": lat,
                "longitude": lon,
                "positional_accuracy_m": accuracy_m,
                "licence": record["license"],
                "noncommercial_only": "/by-nc/" in str(record["license"]).lower(),
                "region_codes": memberships,
                "boundary_membership_uncertain": not any(region_geometries[code].covers(uncertainty) for code in memberships),
                "worldcover_class_2021_at_reported_point": land_class,
                "candidate_only": True,
            })

    OUTPUT = Path("data/research/phase1-observation-candidates.json")
    OUTPUT.write_text(json.dumps(accepted, indent=2) + "\n", encoding="utf-8")
    area_features = []
    for code, region in REGIONS.items():
        geom = transform(lambda x, y, z=None: (x / (M_PER_DEGREE * LON_SCALE), y / M_PER_DEGREE), region_geometries[code])
        area_features.append({
            "type": "Feature",
            "geometry": mapping(geom),
            "properties": {
                "code": code,
                "name": region["label"],
                "boundary_type": "Protected-area snapshot boundary (PM GatiShakti 2024; area discrepancy unresolved)" if code == "mukurthi" else f"WildTrack study area: Survey of India reserve-forest polygons clipped to a {args.forest_selection_radius_m} m landmark search area",
                "data_source": "PM GatiShakti 2024 / State Forest Department Data" if code == "mukurthi" else "Survey of India forest features via BharatAtlas",
                "selection_radius_m": region["radius_m"],
                "source_features": region_sources[code],
            },
        })
    AREA_OUTPUT = Path("data/research/phase1-study-regions.geojson")
    AREA_OUTPUT.write_text(json.dumps({"type": "FeatureCollection", "features": area_features}, separators=(",", ":")), encoding="utf-8")

    species_counts = Counter(row["species"] for row in accepted)
    taxonomic_class_counts = Counter(row["class"] or "Unclassified" for row in accepted)
    region_counts = Counter(code for row in accepted for code in row["region_codes"])
    license_counts = Counter(row["licence"] for row in accepted)
    dataset_dois = sorted({row["dataset_doi"] for row in accepted if row.get("dataset_doi")})
    mukurthi_features = json.loads(MUKURTHI.read_text(encoding="utf-8"))["features"]
    geod = Geod(ellps="WGS84")
    mukurthi_area_km2 = sum(
        abs(geod.geometry_area_perimeter(shape(feature["geometry"]))[0])
        for feature in mukurthi_features
    ) / 1_000_000
    mukurthi_source_area_km2 = float(mukurthi_features[0]["properties"].get("area_sqkm", 0) or 0)
    report = {
        "phase": "1 - real-data source and boundary validation (complete)",
        "candidate_source": "GBIF occurrence search API; source-screened observation candidates are direct human observations, species-level, dated, with stated coordinate uncertainty <=1 km and an explicit Creative Commons licence. They are not expert-verified identifications or individual animal records.",
        "candidate_source_retrieval_method": f"Spatially bounded GBIF query over 76.35-76.90 E, 11.15-11.57 N; 2020-2026; Animalia only; intersected locally with selected reserve-forest blocks and the GatiShakti Mukurthi polygon. For five focus regions, mapped reserve blocks are selected by intersection with a {args.forest_selection_radius_m} m landmark search area.",
        "candidate_source_hash": sha256(OCCURRENCES),
        "artifacts": {
            "observation_candidates": {"path": str(OUTPUT), "sha256": sha256(OUTPUT)},
            "study_regions": {"path": str(AREA_OUTPUT), "sha256": sha256(AREA_OUTPUT)},
            "dataset_metadata": {"path": str(DATASET_METADATA), "sha256": sha256(DATASET_METADATA)},
            "forest_feature_source": {"path": str(FORESTS), "sha256": sha256(FORESTS)},
            "mukurthi_geometry_source": {"path": str(MUKURTHI), "sha256": sha256(MUKURTHI)},
            "worldcover_crop": {"path": str(WORLD_COVER), "sha256": sha256(WORLD_COVER)},
        },
        "source_register": [
            {
                "name": "GBIF occurrence search API",
                "url": "https://api.gbif.org/v1/occurrence/search",
                "use": "Public observation records and dataset metadata; record-level source IDs and citations are retained in the candidate file.",
            },
            {
                "name": "BharatAtlas Survey of India forest features",
                "url": "https://bharatlas.com/",
                "use": "Cartographic reserved-forest features clipped into five WildTrack study extents; not cadastral or legal boundary data.",
                "license": "CC0 as stated by BharatAtlas",
            },
            {
                "name": "PM GatiShakti Mukurthi National Park snapshot 2024",
                "url": "https://bharatlas.com/",
                "use": "Protected-area polygon snapshot; geometry area differs from the source-reported 78.46 km2 and needs reconciliation before authoritative use.",
                "license": "CC0 as stated by BharatAtlas",
            },
            {
                "name": "ESA WorldCover 2021 v200",
                "url": "https://esa-worldcover.org/en/data-access",
                "use": "Modelled land-cover class at reported observation coordinates; not used as a legal forest boundary or hazard classification.",
                "doi": "10.5281/zenodo.7254221",
                "license": "CC BY 4.0",
            },
            {
                "name": "Mukurthi source-reported protected-area area",
                "url": "https://moef.gov.in/uploads/2020/12/minutes-of-43rd-meeting.pdf",
                "use": "MoEFCC meeting record reports Mukurthi National Park area as 78.46 km2.",
            },
        ],
        "source_screened_observation_candidate_count": len(accepted),
        "unique_species_count": len(species_counts),
        "source_dataset_dois_used": dataset_dois,
        "taxonomic_class_counts": dict(taxonomic_class_counts),
        "record_count_by_region_membership": dict(region_counts),
        "record_count_by_licence": dict(license_counts),
        "date_range": [min((row["observed_on"] for row in accepted), default=None), max((row["observed_on"] for row in accepted), default=None)],
        "landcover_classes_at_reported_locations": dict(landcover_counts),
        "screening_counts": dict(screening_counts),
        "boundary_membership": {
            "reported_coordinate_inside_region": len(accepted),
            "full_coordinate_uncertainty_circle_inside_region": sum(not row["boundary_membership_uncertain"] for row in accepted),
            "uncertainty_circle_crosses_region_edge": sum(row["boundary_membership_uncertain"] for row in accepted),
        },
        "boundaries": {
            "study_regions_geojson": str(AREA_OUTPUT),
            "study_regions_sha256": sha256(AREA_OUTPUT),
            "region_areas_km2": {code: round(geometry.area / 1_000_000, 3) for code, geometry in region_geometries.items()},
            "regions": {code: {"label": value["label"], "source_features": region_sources[code]} for code, value in REGIONS.items()},
            "mukurthi_source_reported_area_km2": mukurthi_source_area_km2,
            "mukurthi_polygon_geodesic_area_km2": round(mukurthi_area_km2, 3),
            "mukurthi_geometry_area_difference_percent": round((mukurthi_area_km2 / mukurthi_source_area_km2 - 1) * 100, 2) if mukurthi_source_area_km2 else None,
        },
        "checks": {
            "species_level_taxon": "passed for included records",
            "observation_date_present": "passed for included records",
            "public_unobscured_location": "passed for included records",
            "coordinate_accuracy_at_most_1000m": "passed for included records",
            "record_licence_creative_commons_explicit": "passed; CC BY-NC records are restricted to non-commercial reuse and must keep attribution",
            "uncertainty_buffer_inside_source_boundary": "coordinates are inside by reported point; boundary_membership_uncertain marks reports whose uncertainty radius crosses the polygon edge",
            "GBIF_duplicate_crosswalk": "GBIF occurrence keys deduplicate records in this API result; potential duplicate source records between separate GBIF dataset keys require cross-provider DOI/occurrence review",
            "taxon_manual_expert_review": "not performed; these remain candidates, not expert-verified identifications",
            "source_boundary_scale_and_currentness": "Survey of India features are cartographic; protected-area polygon is a 2024 snapshot; neither is cadastral demarcation",
        },
        "phase_1_outcome": "The research package is ready for Phase 2 application data modelling and import preparation. Region boundaries are mapped study extents, the observation records remain source-screened candidates, and thematic hazard/terrain zones are still to be derived in the next phase.",
        "limitation": "These are sourced occurrence candidates for a classroom map layer, not telemetry or proof that an individually tagged animal lives at the displayed coordinate. Do not call the records live, tagged animals, or movement tracks. For five regions, the stated local buffer clips mapped reserve-forest polygons; it defines a WildTrack analysis area, not an official forest boundary. Focus buffers can overlap. The Mukurthi snapshot geometry's geodesic area differs from the source-reported area; verify the boundary before using it for legal or conservation decisions.",
    }
    Path("data/research/phase1-validation-report.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"candidate_records_screened": len(candidates), "observation_candidates_in_study_extents": len(accepted), "unique_species": len(species_counts), "classes": dict(taxonomic_class_counts), "landcover": dict(landcover_counts), "screening_counts": dict(screening_counts), "region_feature_counts": {key: len(value) for key, value in region_sources.items()}}, indent=2))


if __name__ == "__main__":
    main()
