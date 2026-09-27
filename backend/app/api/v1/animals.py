from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from backend.app.db.postgres.session import get_postgres_session
from backend.app.schemas.api import AnimalOut, DistanceOut, MovementOut, NearbyAnimalOut, TimelineOut, ZoneHistoryOut
from backend.app.services.animals import get_animal, list_animals, resolve_animal_id
from backend.app.services.observations import distance_for_animal, list_observations, movement_for_animal, timeline_for_animal, zone_history_for_animal
from backend.app.services.spatial import animals_near_location


router = APIRouter(prefix="/animals", tags=["animals"])


@router.get("", response_model=list[AnimalOut])
def get_animals(session: Session = Depends(get_postgres_session)) -> list[dict[str, object]]:
    return list_animals(session.connection())


@router.get("/nearby", response_model=list[NearbyAnimalOut])
def get_animals_nearby(
    latitude: float,
    longitude: float,
    radius_meters: float = Query(1000, gt=0, le=20000),
    session: Session = Depends(get_postgres_session),
) -> list[dict[str, object]]:
    return animals_near_location(session.connection(), longitude, latitude, radius_meters)


@router.get("/{animal_id}", response_model=AnimalOut)
def get_animal_detail(animal_id: str, session: Session = Depends(get_postgres_session)) -> dict[str, object]:
    animal = get_animal(session.connection(), animal_id)
    if not animal:
        raise HTTPException(status_code=404, detail="Animal not found")
    return animal


@router.get("/{animal_id}/location")
def get_animal_location(animal_id: str, session: Session = Depends(get_postgres_session)) -> dict[str, object]:
    animal = get_animal(session.connection(), animal_id)
    if not animal:
        raise HTTPException(status_code=404, detail="Animal not found")
    observation = animal.get("latest_observation")
    if not observation:
        raise HTTPException(status_code=404, detail="No location available for animal")
    return {
        "animal_id": animal["animal_id"],
        "species": animal["species"],
        "latitude": observation["latitude"],
        "longitude": observation["longitude"],
        "current_zone": animal.get("current_zone"),
        "observed_at": observation["observed_at"],
    }


@router.get("/{animal_id}/observations")
def get_animal_observations(
    animal_id: str,
    start_time: datetime | None = None,
    end_time: datetime | None = None,
    limit: int = Query(200, ge=1, le=1000),
    order: str = Query("asc", pattern="^(asc|desc)$"),
    session: Session = Depends(get_postgres_session),
) -> list[dict[str, object]]:
    _validate_time_range(start_time, end_time)
    resolved_id = resolve_animal_id(session.connection(), animal_id)
    if not resolved_id:
        raise HTTPException(status_code=404, detail="Animal not found")
    return list_observations(session.connection(), resolved_id, start_time, end_time, limit, descending=order == "desc")


@router.get("/{animal_id}/movement", response_model=MovementOut)
def get_animal_movement(
    animal_id: str,
    start_time: datetime | None = None,
    end_time: datetime | None = None,
    limit: int = Query(500, ge=1, le=2000),
    order: str = Query("asc", pattern="^(asc|desc)$"),
    session: Session = Depends(get_postgres_session),
) -> dict[str, object]:
    _validate_time_range(start_time, end_time)
    resolved_id = resolve_animal_id(session.connection(), animal_id)
    if not resolved_id:
        raise HTTPException(status_code=404, detail="Animal not found")
    return movement_for_animal(session.connection(), resolved_id, start_time, end_time, limit, descending=order == "desc")


@router.get("/{animal_id}/zone-history", response_model=ZoneHistoryOut)
def get_animal_zone_history(
    animal_id: str,
    start_time: datetime | None = None,
    end_time: datetime | None = None,
    limit: int = Query(2000, ge=1, le=5000),
    session: Session = Depends(get_postgres_session),
) -> dict[str, object]:
    _validate_time_range(start_time, end_time)
    resolved_id = resolve_animal_id(session.connection(), animal_id)
    if not resolved_id:
        raise HTTPException(status_code=404, detail="Animal not found")
    return zone_history_for_animal(session.connection(), resolved_id, start_time, end_time, limit)


@router.get("/{animal_id}/timeline", response_model=TimelineOut)
def get_animal_timeline(
    animal_id: str,
    start_time: datetime | None = None,
    end_time: datetime | None = None,
    limit: int = Query(2000, ge=1, le=5000),
    session: Session = Depends(get_postgres_session),
) -> dict[str, object]:
    _validate_time_range(start_time, end_time)
    resolved_id = resolve_animal_id(session.connection(), animal_id)
    if not resolved_id:
        raise HTTPException(status_code=404, detail="Animal not found")
    return timeline_for_animal(session.connection(), resolved_id, start_time, end_time, limit)


@router.get("/{animal_id}/distance", response_model=DistanceOut)
def get_animal_distance(
    animal_id: str,
    start_time: datetime | None = None,
    end_time: datetime | None = None,
    limit: int = Query(2000, ge=1, le=5000),
    session: Session = Depends(get_postgres_session),
) -> dict[str, object]:
    _validate_time_range(start_time, end_time)
    resolved_id = resolve_animal_id(session.connection(), animal_id)
    if not resolved_id:
        raise HTTPException(status_code=404, detail="Animal not found")
    return distance_for_animal(session.connection(), resolved_id, start_time, end_time, limit)


def _validate_time_range(start_time: datetime | None, end_time: datetime | None) -> None:
    if start_time and end_time and start_time > end_time:
        raise HTTPException(status_code=400, detail="start_time must be before end_time")
