from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.app.api.v1.router import api_router
from backend.app.core.config import get_settings
from backend.app.services.health import database_health
from backend.app.services.simulation import simulator


app = FastAPI(title="WildTrack Backend", version="0.2.0")
settings = get_settings()
origins = [origin.strip() for origin in settings.app_cors_origins.split(",") if origin.strip()]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins or ["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(api_router)


@app.get("/health")
def health() -> dict[str, object]:
    return database_health()


@app.on_event("shutdown")
async def shutdown() -> None:
    if simulator.running:
        await simulator.stop()
