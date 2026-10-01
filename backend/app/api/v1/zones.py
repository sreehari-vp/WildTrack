from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from backend.app.db.postgres.session import get_postgres_session
from backend.app.schemas.api import AlertOut, AnimalOut, NearbyZoneOut, ZoneOut
from backend.app.services.alerts import list_alerts_for_zone
from backend.app.services.spatial import zone_containing_point, zones_near_location
from backend.app.services.zones import animals_currently_in_zone, get_zone, list_zones, recent_zone_transitions


router = APIRouter(prefix="/zones", tags=["zones"])


@router.get("", response_model=list[ZoneOut])
def get_zones(session: Session = Depends(get_postgres_session)) -> list[dict[str, object]]:
    return list_zones(session.connection())


@router.get("/lookup")
def lookup_zone(latitude: float, longitude: float, session: Session = Depends(get_postgres_session)) -> dict[str, object] | None:
    zones = zone_containing_point(session.connection(), longitude, latitude)
    return zones[0] if zones else None


@router.get("/nearby", response_model=list[NearbyZoneOut])
def get_nearby_zones(
    latitude: float,
    longitude: float,
    radius_meters: float = Query(1000, gt=0, le=20000),
    session: Session = Depends(get_postgres_session),
) -> list[dict[str, object]]:
    return zones_near_location(session.connection(), longitude, latitude, radius_meters)


@router.get("/{zone_id}", response_model=ZoneOut)
def get_zone_detail(zone_id: str, session: Session = Depends(get_postgres_session)) -> dict[str, object]:
    zone = get_zone(session.connection(), zone_id)
    if not zone:
        raise HTTPException(status_code=404, detail="Zone not found")
    return zone


@router.get("/{zone_id}/animals", response_model=list[AnimalOut])
def get_zone_animals(zone_id: str, session: Session = Depends(get_postgres_session)) -> list[dict[str, object]]:
    if not get_zone(session.connection(), zone_id):
        raise HTTPException(status_code=404, detail="Zone not found")
    return animals_currently_in_zone(session.connection(), zone_id)


@router.get("/{zone_id}/transitions")
def get_zone_transitions(
    zone_id: str,
    limit: int = Query(20, ge=1, le=100),
    session: Session = Depends(get_postgres_session),
) -> list[dict[str, object]]:
    if not get_zone(session.connection(), zone_id):
        raise HTTPException(status_code=404, detail="Zone not found")
    return recent_zone_transitions(session.connection(), zone_id, limit)


@router.get("/{zone_id}/alerts", response_model=list[AlertOut])
def get_zone_alerts(
    zone_id: str,
    limit: int = Query(100, ge=1, le=500),
    session: Session = Depends(get_postgres_session),
) -> list[dict[str, object]]:
    if not get_zone(session.connection(), zone_id):
        raise HTTPException(status_code=404, detail="Zone not found")
    return list_alerts_for_zone(session.connection(), zone_id, limit)
