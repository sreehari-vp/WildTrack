"""Read the Aura movement projection; PostgreSQL remains the source of truth."""

import asyncio
import logging
from datetime import date

from fastapi import APIRouter, HTTPException, Query

from backend.app.services.movement_network import (
    configured, corridor_detail, habitat_impact, network_snapshot,
    projection_status, sync_projection,
)

router = APIRouter(prefix="/network", tags=["movement network"])
logger = logging.getLogger(__name__)


def _require_configured() -> None:
    if not configured():
        raise HTTPException(503, "Neo4j Aura is not configured in the backend .env file")


def _dates(start_date: date | None, end_date: date | None) -> tuple[str | None, str | None]:
    if start_date and end_date and start_date > end_date:
        raise HTTPException(400, "start_date must not be after end_date")
    return start_date.isoformat() if start_date else None, end_date.isoformat() if end_date else None


def _unavailable(exc: Exception) -> HTTPException:
    logger.warning("Movement network unavailable (%s)", type(exc).__name__)
    return HTTPException(503, "Neo4j Aura is unavailable; PostgreSQL monitoring remains available")


@router.get("/status")
def get_network_status():
    try:
        return projection_status()
    except Exception as exc:
        raise _unavailable(exc) from None


@router.get("")
def get_network(species: str | None = None, start_date: date | None = None,
                end_date: date | None = None):
    start, end = _dates(start_date, end_date)
    try:
        return network_snapshot(species=species, start_date=start, end_date=end)
    except Exception as exc:
        raise _unavailable(exc) from None


@router.post("/sync")
async def sync_network(force: bool = False):
    _require_configured()
    try:
        return await asyncio.to_thread(sync_projection, force=force)
    except RuntimeError as exc:
        if "already running" in str(exc):
            raise HTTPException(409, "A network synchronization is already running") from None
        raise _unavailable(exc) from None
    except Exception as exc:
        raise _unavailable(exc) from None


@router.get("/corridors/{from_zone_id}/{to_zone_id}")
def get_corridor(from_zone_id: str, to_zone_id: str, species: str | None = None,
                 start_date: date | None = None, end_date: date | None = None):
    _require_configured()
    start, end = _dates(start_date, end_date)
    try:
        return corridor_detail(from_zone_id, to_zone_id, species=species,
                               start_date=start, end_date=end)
    except Exception as exc:
        raise _unavailable(exc) from None


@router.get("/impact/{zone_id}")
def get_habitat_impact(zone_id: str, max_hops: int = Query(3, ge=1, le=3)):
    _require_configured()
    try:
        return habitat_impact(zone_id, max_hops=max_hops)
    except KeyError:
        raise HTTPException(404, "Zone is not present in the movement network") from None
    except Exception as exc:
        raise _unavailable(exc) from None
