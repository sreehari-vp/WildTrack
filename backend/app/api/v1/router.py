from fastapi import APIRouter
from fastapi import Depends, HTTPException
from sqlalchemy import text
from sqlalchemy.orm import Session
from backend.app.db.postgres.session import get_postgres_session

from backend.app.api.v1.alerts import router as alerts_router
from backend.app.api.v1.analytics import router as analytics_router
from backend.app.api.v1.animals import router as animals_router
from backend.app.api.v1.observations import router as observations_router
from backend.app.api.v1.simulation import router as simulation_router
from backend.app.api.v1.monitoring_state import router as monitoring_state_router
from backend.app.api.v1.monitoring_history import router as monitoring_history_router
from backend.app.api.v1.network import router as network_router
from backend.app.api.v1.zones import router as zones_router


api_router = APIRouter(prefix="/api/v1")
api_router.include_router(alerts_router)
api_router.include_router(analytics_router)
api_router.include_router(animals_router)
api_router.include_router(observations_router)
api_router.include_router(zones_router)
api_router.include_router(simulation_router)
api_router.include_router(monitoring_state_router)
api_router.include_router(monitoring_history_router)
api_router.include_router(network_router)


@api_router.get("/boundaries")
def get_boundary(session: Session = Depends(get_postgres_session)):
    geometry = session.execute(text(
        "SELECT ST_AsGeoJSON(ST_Multi(ST_Union(geometry)))::json FROM forest_boundaries"
    )).scalar_one_or_none()
    if geometry is None:
        raise HTTPException(404, "No reserve boundary has been configured")
    return geometry
