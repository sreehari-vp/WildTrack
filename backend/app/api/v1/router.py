from fastapi import APIRouter

from backend.app.api.v1.alerts import router as alerts_router
from backend.app.api.v1.animals import router as animals_router
from backend.app.api.v1.observations import router as observations_router
from backend.app.api.v1.simulation import router as simulation_router
from backend.app.api.v1.zones import router as zones_router


api_router = APIRouter(prefix="/api/v1")
api_router.include_router(alerts_router)
api_router.include_router(animals_router)
api_router.include_router(observations_router)
api_router.include_router(zones_router)
api_router.include_router(simulation_router)
