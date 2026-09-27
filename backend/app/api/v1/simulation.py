from fastapi import APIRouter

from backend.app.schemas.api import SimulationStatus
from backend.app.services.simulation import simulator


router = APIRouter(prefix="/simulation", tags=["simulation"])


@router.post("/start")
async def start_simulation() -> dict[str, object]:
    started = await simulator.start()
    return {"running": simulator.running, "started": started, "message": "Simulator already running" if not started else "Simulator started"}


@router.post("/stop")
async def stop_simulation() -> dict[str, object]:
    stopped = await simulator.stop()
    return {"running": simulator.running, "stopped": stopped, "message": "Simulator was not running" if not stopped else "Simulator stopped"}


@router.post("/reset")
async def reset_simulation() -> dict[str, object]:
    await simulator.reset()
    return {"running": simulator.running, "reset": True}


@router.get("/status", response_model=SimulationStatus)
def simulation_status() -> SimulationStatus:
    return simulator.status()
