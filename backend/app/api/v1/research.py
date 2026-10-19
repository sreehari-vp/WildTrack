"""Read-only access to sourced Ooty study areas and historical sightings."""

from fastapi import APIRouter, Depends, Query
from typing import Literal
from sqlalchemy import text
from sqlalchemy.orm import Session

from backend.app.db.postgres.session import get_postgres_session


router = APIRouter(prefix="/research", tags=["research"])
V2_CODES = {
    "wenlock_downs", "naduvattam", "porthimund", "kundah",
    "mukurthi_lake", "nilgiri_peak", "doddabetta_forest", "kalhatty",
}


def selected_region_codes(connection, dataset: str) -> set[str]:
    codes = set(connection.execute(text("select code from public.study_regions")).scalars())
    if dataset == "all":
        return codes
    if dataset == "previous":
        return codes - V2_CODES
    return codes & V2_CODES if codes & V2_CODES else codes


@router.get("/areas")
def research_areas(
    land_cover: bool = False,
    dataset: Literal["current", "previous", "all"] = "current",
    session: Session = Depends(get_postgres_session),
) -> dict[str, object]:
    connection = session.connection()
    selected_codes = sorted(selected_region_codes(connection, dataset))
    regions = connection.execute(text("""
        select code, name, boundary_type, description, data_source, source_url,
               source_license, source_version, selection_radius_m,
               round((ST_Area(geometry::geography) / 1000000)::numeric, 3) as area_sq_km,
               ST_AsGeoJSON(geometry)::jsonb as geometry
        from public.study_regions where code = any(:selected_codes) order by name
    """), {"selected_codes": selected_codes}).mappings().all()
    features = [
        {
            "type": "Feature", "id": f"region:{row['code']}", "geometry": row["geometry"],
            "properties": {**{key: value for key, value in row.items() if key != "geometry"}, "kind": "region"},
        }
        for row in regions
    ]
    if land_cover:
        zones = connection.execute(text("""
        select z.code, z.study_region_code, z.zone_type, z.name, z.description, z.data_source,
               z.source_url, z.source_license, z.source_version, z.resolution_m, z.area_sq_km,
               attention.risk_level, ST_AsGeoJSON(z.geometry)::jsonb as geometry
        from public.thematic_zones z
        left join lateral (
            select active_zone.risk_level
            from public.zones active_zone
            where active_zone.study_region_code=z.study_region_code
              and active_zone.zone_type=z.zone_type
              and active_zone.created_in_app=false
            order by active_zone.zone_id
            limit 1
        ) attention on true
        where z.study_region_code = any(:selected_codes)
        order by z.study_region_code, z.zone_type
        """), {"selected_codes": selected_codes}).mappings().all()
        features.extend(
            {
                "type": "Feature", "id": f"land-cover:{row['code']}", "geometry": row["geometry"],
                "properties": {**{key: value for key, value in row.items() if key != "geometry"}, "kind": "land_cover"},
            }
            for row in zones
        )
    return {"type": "FeatureCollection", "features": features}


@router.get("/occurrences")
def research_occurrences(
    limit: int = Query(500, ge=1, le=500),
    dataset: Literal["current", "previous", "all"] = "current",
    session: Session = Depends(get_postgres_session),
) -> dict[str, object]:
    connection = session.connection()
    selected_codes = sorted(selected_region_codes(connection, dataset))
    rows = connection.execute(text("""
        select o.id, o.source_system, o.source_record_id, o.species, o.scientific_name,
               o.taxonomic_class, o.source_observed_at, o.observed_at, o.coordinate_uncertainty_m,
               o.license_uri, o.noncommercial_only, o.source_url, o.worldcover_class_2021,
               d.title as dataset_title, d.doi as dataset_doi, d.citation as dataset_citation,
               ST_X(o.location) as longitude, ST_Y(o.location) as latitude,
               coalesce((
                   select jsonb_agg(jsonb_build_object(
                       'code', r.code, 'name', r.name,
                       'uncertainty_crosses_boundary', m.uncertainty_crosses_boundary
                   ) order by r.name)
                   from public.occurrence_region_memberships m
                   join public.study_regions r on r.code = m.study_region_code
                   where m.occurrence_id = o.id
                     and m.study_region_code = any(:selected_codes)
               ), '[]'::jsonb) as regions
        from public.wildlife_occurrences o
        join public.research_datasets d on d.dataset_key = o.dataset_key
        where exists (
            select 1 from public.occurrence_region_memberships m2
            where m2.occurrence_id = o.id
              and m2.study_region_code = any(:selected_codes)
        )
        order by o.observed_at desc, o.id desc
        limit :limit
    """), {"limit": limit, "selected_codes": selected_codes}).mappings().all()
    return {"count": len(rows), "occurrences": [dict(row) for row in rows]}
