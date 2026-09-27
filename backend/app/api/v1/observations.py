from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from backend.app.db.postgres.session import get_postgres_session
from backend.app.schemas.api import ObservationOut
from backend.app.services.observations import list_observations


router = APIRouter(prefix="/observations", tags=["observations"])


@router.get("", response_model=list[ObservationOut])
def get_observations(
    animal_id: str | None = None,
    start_time: datetime | None = None,
    end_time: datetime | None = None,
    limit: int = Query(200, ge=1, le=1000),
    session: Session = Depends(get_postgres_session),
) -> list[dict[str, object]]:
    if start_time and end_time and start_time > end_time:
        raise HTTPException(status_code=400, detail="start_time must be before end_time")
    return list_observations(session.connection(), animal_id, start_time, end_time, limit, descending=True)
