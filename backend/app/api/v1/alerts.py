from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from backend.app.db.postgres.session import get_postgres_session
from backend.app.schemas.api import AlertOut, AlertStatusUpdate
from backend.app.services.alerts import get_alert, list_alerts, update_alert_status


router = APIRouter(prefix="/alerts", tags=["alerts"])


@router.get("", response_model=list[AlertOut])
def get_alerts(
    severity: str | None = None,
    status: str | None = None,
    animal_id: str | None = None,
    zone_id: str | None = None,
    start_time: datetime | None = None,
    end_time: datetime | None = None,
    limit: int = Query(200, ge=1, le=500),
    session: Session = Depends(get_postgres_session),
) -> list[dict[str, object]]:
    _validate_time_range(start_time, end_time)
    return list_alerts(
        session.connection(),
        severity=severity,
        status=status,
        animal_id=animal_id,
        zone_id=zone_id,
        start_time=start_time,
        end_time=end_time,
        limit=limit,
    )


@router.get("/{alert_id}", response_model=AlertOut)
def get_alert_detail(alert_id: str, session: Session = Depends(get_postgres_session)) -> dict[str, object]:
    alert = get_alert(session.connection(), alert_id)
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")
    return alert


@router.patch("/{alert_id}", response_model=AlertOut)
def patch_alert_status(
    alert_id: str,
    payload: AlertStatusUpdate,
    session: Session = Depends(get_postgres_session),
) -> dict[str, object]:
    conn = session.connection()
    try:
        alert = update_alert_status(conn, alert_id, payload.status)
        session.commit()
    except ValueError as exc:
        session.rollback()
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except RuntimeError as exc:
        session.rollback()
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")
    return alert


def _validate_time_range(start_time: datetime | None, end_time: datetime | None) -> None:
    if start_time and end_time and start_time > end_time:
        raise HTTPException(status_code=400, detail="start_time must be before end_time")
