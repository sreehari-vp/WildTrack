from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy import text
from sqlalchemy.engine import Connection


ACTIVE_ALERT_STATUSES = ("open", "acknowledged")
VALID_ALERT_STATUSES = ("open", "acknowledged", "resolved")


def list_alerts(
    conn: Connection,
    *,
    severity: str | None = None,
    status: str | None = None,
    animal_id: str | None = None,
    zone_id: str | None = None,
    start_time: datetime | None = None,
    end_time: datetime | None = None,
    limit: int = 200,
) -> list[dict[str, object]]:
    clauses = []
    params: dict[str, object] = {"limit": min(limit, 500)}
    if severity:
        clauses.append("al.severity = :severity")
        params["severity"] = severity
    if status:
        clauses.append("al.status = :status")
        params["status"] = status
    if animal_id:
        clauses.append("(al.animal_id = :animal_id OR a.animal_code = :animal_id)")
        params["animal_id"] = animal_id
    if zone_id:
        clauses.append("al.zone_id = :zone_id")
        params["zone_id"] = zone_id
    if start_time:
        clauses.append("al.created_at >= :start_time")
        params["start_time"] = start_time
    if end_time:
        clauses.append("al.created_at <= :end_time")
        params["end_time"] = end_time
    where_sql = f"WHERE {' AND '.join(clauses)}" if clauses else ""
    rows = conn.execute(text(f"{ALERT_QUERY} {where_sql} ORDER BY al.created_at DESC LIMIT :limit"), params).mappings()
    return [_alert_from_row(dict(row)) for row in rows]


def get_alert(conn: Connection, alert_id: str) -> dict[str, object] | None:
    row = conn.execute(
        text(f"{ALERT_QUERY} WHERE al.alert_id = :alert_id LIMIT 1"),
        {"alert_id": alert_id},
    ).mappings().first()
    return _alert_from_row(dict(row)) if row else None


def list_alerts_for_animal(conn: Connection, animal_ref: str, limit: int = 100) -> list[dict[str, object]]:
    return list_alerts(conn, animal_id=animal_ref, limit=limit)


def list_alerts_for_zone(conn: Connection, zone_id: str, limit: int = 100) -> list[dict[str, object]]:
    return list_alerts(conn, zone_id=zone_id, limit=limit)


def find_active_duplicate_alert(
    conn: Connection,
    *,
    animal_id: str,
    zone_id: str | None,
    rule_id: str,
    alert_type: str,
) -> dict[str, object] | None:
    row = conn.execute(
        text(
            f"""
            {ALERT_QUERY}
            WHERE al.animal_id = :animal_id
              AND al.rule_id = :rule_id
              AND al.alert_type = :alert_type
              AND al.status = ANY(:active_statuses)
              AND al.zone_id IS NOT DISTINCT FROM :zone_id
            ORDER BY al.created_at DESC
            LIMIT 1
            """
        ),
        {
            "animal_id": animal_id,
            "zone_id": zone_id,
            "rule_id": rule_id,
            "alert_type": alert_type,
            "active_statuses": list(ACTIVE_ALERT_STATUSES),
        },
    ).mappings().first()
    return _alert_from_row(dict(row)) if row else None


def create_alert(
    conn: Connection,
    *,
    animal_id: str,
    zone_id: str | None,
    rule_id: str,
    alert_type: str,
    severity: str,
    message: str,
) -> dict[str, object]:
    alert_id = f"ALT-ECA-{uuid4().hex[:16].upper()}"
    conn.execute(
        text(
            """
            INSERT INTO alerts
            (alert_id, animal_id, zone_id, rule_id, alert_type, severity, message, status, resolved_at)
            VALUES (:alert_id, :animal_id, :zone_id, :rule_id, :alert_type, :severity, :message, 'open', NULL)
            """
        ),
        {
            "alert_id": alert_id,
            "animal_id": animal_id,
            "zone_id": zone_id,
            "rule_id": rule_id,
            "alert_type": alert_type,
            "severity": severity,
            "message": message,
        },
    )
    alert = get_alert(conn, alert_id)
    assert alert is not None
    return alert


def update_alert_status(conn: Connection, alert_id: str, status: str) -> dict[str, object] | None:
    normalized_status = status.lower()
    if normalized_status not in VALID_ALERT_STATUSES:
        raise ValueError("Invalid alert status")

    existing = get_alert(conn, alert_id)
    if not existing:
        return None
    current_status = str(existing["status"])
    if current_status == "resolved" and normalized_status == "resolved":
        raise RuntimeError("Alert is already resolved")
    if current_status == "resolved" and normalized_status != "resolved":
        raise RuntimeError("Resolved alerts cannot be reopened")
    if current_status == "acknowledged" and normalized_status == "open":
        raise RuntimeError("Acknowledged alerts cannot return to open")

    resolved_at = datetime.now(timezone.utc) if normalized_status == "resolved" else None
    conn.execute(
        text(
            """
            UPDATE alerts
            SET status = :status,
                resolved_at = :resolved_at,
                updated_at = now()
            WHERE alert_id = :alert_id
            """
        ),
        {"alert_id": alert_id, "status": normalized_status, "resolved_at": resolved_at},
    )
    return get_alert(conn, alert_id)


ALERT_QUERY = """
SELECT
    al.alert_id, al.animal_id, al.zone_id, al.rule_id, al.alert_type,
    al.severity, al.message, al.status, al.created_at, al.updated_at, al.resolved_at,
    a.animal_code, a.name AS animal_name, a.species,
    z.zone_name, z.zone_type,
    r.rule_name
FROM alerts al
LEFT JOIN animals a ON a.animal_id = al.animal_id
LEFT JOIN zones z ON z.zone_id = al.zone_id
LEFT JOIN eca_rules r ON r.rule_id = al.rule_id
"""


def _alert_from_row(row: dict[str, object]) -> dict[str, object]:
    return {
        "alert_id": row["alert_id"],
        "animal_id": row["animal_id"],
        "zone_id": row["zone_id"],
        "rule_id": row["rule_id"],
        "alert_type": row["alert_type"],
        "severity": row["severity"],
        "message": row["message"],
        "status": row["status"],
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
        "resolved_at": row["resolved_at"],
        "animal_code": row.get("animal_code"),
        "animal_name": row.get("animal_name"),
        "species": row.get("species"),
        "zone_name": row.get("zone_name"),
        "zone_type": row.get("zone_type"),
        "rule_name": row.get("rule_name"),
    }
