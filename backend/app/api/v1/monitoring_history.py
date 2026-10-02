"""Versioned configuration and current monitoring health."""

import asyncio
import json
from datetime import datetime, timezone
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import StreamingResponse
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from backend.app.db.postgres.session import SessionLocal, get_postgres_session
from backend.app.schemas.api import RuleOut, RuleWrite

router = APIRouter(tags=["monitoring history"])


def _rule(session: Session, rule_id: str) -> dict | None:
    row = session.execute(text("""
        SELECT rule_id, rule_name, event_type, condition, action, severity, enabled, version_no
        FROM eca_rules WHERE rule_id=:id
    """), {"id": rule_id}).mappings().first()
    return dict(row) if row else None


@router.get("/rules", response_model=list[RuleOut])
def list_rules(session: Session = Depends(get_postgres_session)):
    return [dict(row) for row in session.execute(text("""
        SELECT rule_id, rule_name, event_type, condition, action, severity, enabled, version_no
        FROM eca_rules ORDER BY rule_id
    """)).mappings()]


@router.post("/rules", response_model=RuleOut, status_code=201)
def create_rule(payload: RuleWrite, session: Session = Depends(get_postgres_session)):
    rule_id = f"RULE-{uuid4().hex[:20].upper()}"
    try:
        session.execute(text("""
            INSERT INTO eca_rules (rule_id, rule_name, event_type, condition, action, severity, enabled)
            VALUES (:id, :name, :event_type, CAST(:condition AS jsonb), CAST(:action AS jsonb), :severity, :enabled)
        """), {"id": rule_id, "name": payload.rule_name.strip(), "event_type": payload.event_type,
               "condition": json.dumps(payload.condition), "action": json.dumps(payload.action),
               "severity": payload.severity, "enabled": payload.enabled})
        session.commit()
    except IntegrityError:
        session.rollback()
        raise HTTPException(409, "A rule with this name already exists") from None
    return _rule(session, rule_id)


@router.put("/rules/{rule_id}", response_model=RuleOut)
def update_rule(rule_id: str, payload: RuleWrite, session: Session = Depends(get_postgres_session)):
    if not _rule(session, rule_id):
        raise HTTPException(404, "Rule not found")
    try:
        session.execute(text("""
            UPDATE eca_rules SET rule_name=:name, event_type=:event_type,
                condition=CAST(:condition AS jsonb), action=CAST(:action AS jsonb),
                severity=:severity, enabled=:enabled
            WHERE rule_id=:id
        """), {"id": rule_id, "name": payload.rule_name.strip(), "event_type": payload.event_type,
               "condition": json.dumps(payload.condition), "action": json.dumps(payload.action),
               "severity": payload.severity, "enabled": payload.enabled})
        session.commit()
    except IntegrityError:
        session.rollback()
        raise HTTPException(409, "A rule with this name already exists") from None
    return _rule(session, rule_id)


def _history_where(at: datetime | None, limit: int, id_name: str, item_id: str):
    if at and at.tzinfo is None:
        raise HTTPException(400, "Use a timezone-qualified timestamp")
    params = {"id": item_id, "limit": limit}
    clause = f"WHERE {id_name}=:id"
    if at:
        clause += " AND valid_from <= :at AND (valid_to IS NULL OR :at < valid_to)"
        params["at"] = at
    return clause, params


@router.get("/zones/{zone_id}/history")
def zone_history(zone_id: str, at: datetime | None = None, limit: int = Query(100, ge=1, le=500),
                 session: Session = Depends(get_postgres_session)):
    clause, params = _history_where(at, limit, "zone_id", zone_id)
    return [dict(row) for row in session.execute(text(f"""
        SELECT zone_id, version_no, valid_from, valid_to, zone_name, zone_type,
               risk_level, description, ST_AsGeoJSON(geometry)::json AS geometry
        FROM zone_versions {clause}
        ORDER BY version_no DESC LIMIT :limit
    """), params).mappings()]


@router.get("/rules/{rule_id}/history")
def rule_history(rule_id: str, at: datetime | None = None, limit: int = Query(100, ge=1, le=500),
                 session: Session = Depends(get_postgres_session)):
    clause, params = _history_where(at, limit, "rule_id", rule_id)
    return [dict(row) for row in session.execute(text(f"""
        SELECT rule_id, version_no, valid_from, valid_to, rule_name, event_type,
               condition, action, severity, enabled
        FROM eca_rule_versions {clause}
        ORDER BY version_no DESC LIMIT :limit
    """), params).mappings()]


@router.get("/monitoring/audit")
def configuration_audit(entity_type: str | None = None, entity_id: str | None = None,
                        limit: int = Query(100, ge=1, le=500), session: Session = Depends(get_postgres_session)):
    if entity_type and entity_type not in {"zones", "eca_rules", "map_pins", "map_preferences"}:
        raise HTTPException(400, "Unknown entity type")
    filters = []
    params: dict = {"limit": limit}
    if entity_type:
        filters.append("entity_type=:entity_type")
        params["entity_type"] = entity_type
    if entity_id:
        filters.append("entity_id=:entity_id")
        params["entity_id"] = entity_id
    where = "WHERE " + " AND ".join(filters) if filters else ""
    return [dict(row) for row in session.execute(text(f"""
        SELECT audit_id, entity_type, entity_id, operation, before_data, after_data, changed_at
        FROM configuration_audit
        {where}
        ORDER BY audit_id DESC LIMIT :limit
    """), params).mappings()]


def _summary(session: Session, hours: int) -> dict:
    conn = session.connection()
    counts = dict(conn.execute(text("""
        SELECT (SELECT count(*) FROM animals WHERE status='active') AS active_animals,
               (SELECT count(*) FROM alerts WHERE status IN ('open','acknowledged')) AS open_alerts,
               (SELECT count(*) FROM event_outbox WHERE delivered_at IS NULL) AS pending_events,
               (SELECT count(*) FROM event_outbox WHERE delivered_at IS NULL AND attempts > 0) AS retrying_events,
               (SELECT max(observed_at) FROM observations) AS latest_observation_at
    """)).mappings().one())
    hourly = [dict(row) for row in conn.execute(text("""
        SELECT bucket_start, observation_count, alert_count, critical_alert_count
        FROM operational_hourly_summary
        WHERE bucket_start >= now() - (:hours * interval '1 hour')
        ORDER BY bucket_start DESC LIMIT :hours
    """), {"hours": hours}).mappings()]
    return {"counts": counts, "hourly": hourly, "generated_at": datetime.now(timezone.utc)}


@router.get("/monitoring/summary")
def monitoring_summary(hours: int = Query(24, ge=1, le=168), session: Session = Depends(get_postgres_session)):
    return _summary(session, hours)


def _stream_signature() -> dict:
    with SessionLocal() as session:
        return dict(session.execute(text("""
            SELECT (SELECT max(observed_at) FROM observations) AS latest_observation_at,
                   (SELECT max(updated_at) FROM alerts) AS latest_alert_at,
                   (SELECT count(*) FROM event_outbox WHERE delivered_at IS NULL) AS pending_events
        """)).mappings().one())


@router.get("/monitoring/stream")
async def monitoring_stream(request: Request):
    async def events():
        previous = None
        heartbeat = 0
        while not await request.is_disconnected():
            try:
                current = await asyncio.to_thread(_stream_signature)
                if current != previous:
                    previous = current
                    yield f"event: update\ndata: {json.dumps(current, default=str)}\n\n"
                elif heartbeat % 8 == 0:
                    yield ": heartbeat\n\n"
            except Exception:
                yield "event: unavailable\ndata: {}\n\n"
            heartbeat += 1
            await asyncio.sleep(2)

    return StreamingResponse(events(), media_type="text/event-stream",
                             headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})
