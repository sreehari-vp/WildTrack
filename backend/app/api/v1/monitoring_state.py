from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from backend.app.db.postgres.session import get_postgres_session
from backend.app.schemas.api import MapPreferences, PinOut, PinWrite, ZoneOut, ZoneWrite
from backend.app.services import monitoring_state as state

router = APIRouter(tags=["monitoring"])


@router.post("/zones", response_model=ZoneOut, status_code=201)
def create_zone(payload: ZoneWrite, session: Session = Depends(get_postgres_session)):
    try:
        return state.create_zone(session, payload)
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc


@router.put("/zones/{zone_id}", response_model=ZoneOut)
def update_zone(zone_id: str, payload: ZoneWrite, session: Session = Depends(get_postgres_session)):
    try:
        zone = state.update_zone(session, zone_id, payload)
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc
    if not zone:
        raise HTTPException(404, "Zone not found")
    return zone


@router.delete("/zones/{zone_id}", status_code=204)
def delete_zone(zone_id: str, session: Session = Depends(get_postgres_session)):
    if not state.delete_zone(session, zone_id):
        raise HTTPException(409, "Only new zones without observation or alert history can be deleted")


@router.get("/pins", response_model=list[PinOut])
def list_pins(session: Session = Depends(get_postgres_session)):
    return state.list_pins(session)


@router.post("/pins", response_model=PinOut, status_code=201)
def create_pin(payload: PinWrite, session: Session = Depends(get_postgres_session)):
    return state.create_pin(session, payload)


@router.delete("/pins/{pin_id}", status_code=204)
def delete_pin(pin_id: str, session: Session = Depends(get_postgres_session)):
    if not state.delete_pin(session, pin_id):
        raise HTTPException(404, "Pin not found")


@router.get("/map/preferences", response_model=MapPreferences)
def get_preferences(session: Session = Depends(get_postgres_session)):
    return state.get_preferences(session)


@router.put("/map/preferences", response_model=MapPreferences)
def save_preferences(payload: MapPreferences, session: Session = Depends(get_postgres_session)):
    return state.save_preferences(session, payload)
