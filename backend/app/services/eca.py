from __future__ import annotations

import logging
from datetime import datetime
from typing import Any

from pymongo.database import Database
from sqlalchemy import text
from sqlalchemy.engine import Connection

from backend.app.services.alerts import create_alert, find_active_duplicate_alert


logger = logging.getLogger(__name__)


ZONE_ENTRY_EVENT_TYPES = {
    "restricted": "restricted_zone_entry",
    "protected": "protected_zone_entry",
    "high-risk": "high_risk_zone_entry",
}


def load_active_rules(conn: Connection, event_type: str | None = None) -> list[dict[str, Any]]:
    params: dict[str, Any] = {}
    where = "WHERE enabled = true"
    if event_type:
        where += " AND event_type = :event_type"
        params["event_type"] = event_type
    rows = conn.execute(
        text(
            f"""
            SELECT rule_id, rule_name, event_type, condition, action, severity, enabled
            FROM eca_rules
            {where}
            ORDER BY rule_id
            """
        ),
        params,
    ).mappings()
    return [dict(row) for row in rows]


def evaluate_observation_context(
    conn: Connection,
    *,
    animal: dict[str, Any],
    observation: dict[str, Any],
    current_zone: dict[str, Any] | None,
    previous_zone_id: str | None,
    mongo_db: Database | None = None,
) -> list[dict[str, Any]]:
    alerts: list[dict[str, Any]] = []
    for event in observation_events(animal=animal, observation=observation, current_zone=current_zone, previous_zone_id=previous_zone_id):
        alerts.extend(evaluate_event(conn, event, mongo_db=mongo_db))
    return alerts


def observation_events(
    *,
    animal: dict[str, Any],
    observation: dict[str, Any],
    current_zone: dict[str, Any] | None,
    previous_zone_id: str | None,
) -> list[dict[str, Any]]:
    base_context = {
        "animal_id": animal["animal_id"],
        "animal_code": animal.get("animal_code", animal["animal_id"]),
        "animal_name": animal.get("name"),
        "species": animal.get("species"),
        "device_id": animal.get("device_id"),
        "battery_level": animal.get("battery_level"),
        "observation_id": observation.get("observation_id"),
        "timestamp": observation.get("observed_at") or observation.get("timestamp"),
        "latitude": observation.get("latitude"),
        "longitude": observation.get("longitude"),
        "speed": observation.get("speed"),
        "previous_zone_id": previous_zone_id,
    }
    if current_zone:
        base_context.update(
            {
                "zone_id": current_zone.get("zone_id"),
                "zone_name": current_zone.get("zone_name") or current_zone.get("name"),
                "zone_type": current_zone.get("zone_type"),
                "risk_level": current_zone.get("risk_level"),
            }
        )

    events: list[dict[str, Any]] = []
    current_zone_id = base_context.get("zone_id")
    if current_zone_id and current_zone_id != previous_zone_id:
        events.append({**base_context, "event_type": "zone_entry"})
        zone_type = str(base_context.get("zone_type") or "").lower()
        risk_level = str(base_context.get("risk_level") or "").lower()
        specific_event_type = ZONE_ENTRY_EVENT_TYPES.get(zone_type)
        if specific_event_type:
            events.append({**base_context, "event_type": specific_event_type})
        if risk_level == "critical" and specific_event_type != "high_risk_zone_entry":
            events.append({**base_context, "event_type": "high_risk_zone_entry"})
    if previous_zone_id and previous_zone_id != current_zone_id:
        events.append({**base_context, "event_type": "zone_exit"})
    if _as_float(base_context.get("battery_level")) is not None:
        events.append({**base_context, "event_type": "low_battery"})
    return events


def evaluate_event(conn: Connection, event: dict[str, Any], mongo_db: Database | None = None) -> list[dict[str, Any]]:
    created_or_existing: list[dict[str, Any]] = []
    for rule in load_active_rules(conn, event_type=str(event["event_type"])):
        if not conditions_match(rule.get("condition") or {}, event):
            continue
        action = rule.get("action") or {}
        if not action.get("create_alert"):
            continue
        duplicate = find_active_duplicate_alert(
            conn,
            animal_id=str(event["animal_id"]),
            zone_id=event.get("zone_id"),
            rule_id=str(rule["rule_id"]),
            alert_type=str(rule["event_type"]),
        )
        if duplicate:
            created_or_existing.append({**duplicate, "duplicate": True})
            continue
        alert = create_alert(
            conn,
            animal_id=str(event["animal_id"]),
            zone_id=event.get("zone_id"),
            rule_id=str(rule["rule_id"]),
            alert_type=str(rule["event_type"]),
            severity=str(rule["severity"]),
            message=build_alert_message(rule, event),
        )
        log_event_to_mongodb(mongo_db, event=event, rule=rule, alert=alert)
        created_or_existing.append({**alert, "duplicate": False})
    return created_or_existing


def conditions_match(conditions: dict[str, Any], context: dict[str, Any]) -> bool:
    for key, expected in conditions.items():
        if key == "zone_type" and _normalize(context.get("zone_type")) != _normalize(expected):
            return False
        if key == "risk_level" and _normalize(context.get("risk_level")) != _normalize(expected):
            return False
        if key == "species" and _normalize(context.get("species")) != _normalize(expected):
            return False
        if key == "battery_level_lt":
            battery_level = _as_float(context.get("battery_level"))
            if battery_level is None or battery_level >= float(expected):
                return False
        if key == "distance_to_boundary_lt":
            distance = _as_float(context.get("distance_to_boundary_meters"))
            if distance is None or distance >= float(expected):
                return False
        if key == "time_in_zone_gt":
            duration = _as_float(context.get("time_in_zone_seconds"))
            if duration is None or duration <= float(expected):
                return False
        if key == "distance_travelled_gt":
            distance = _as_float(context.get("distance_travelled_meters"))
            if distance is None or distance <= float(expected):
                return False
    return True


def build_alert_message(rule: dict[str, Any], event: dict[str, Any]) -> str:
    animal_label = event.get("animal_name") or event.get("animal_code") or event["animal_id"]
    zone_label = event.get("zone_name") or event.get("zone_id") or "the reserve"
    event_type = str(rule["event_type"])
    if event_type == "restricted_zone_entry":
        return f"{animal_label} entered {zone_label}."
    if event_type == "protected_zone_entry":
        return f"{animal_label} entered protected habitat in {zone_label}."
    if event_type == "high_risk_zone_entry":
        return f"{animal_label} entered high-risk terrain in {zone_label}."
    if event_type == "low_battery":
        battery_level = event.get("battery_level")
        return f"{animal_label} tracker battery is below threshold ({battery_level}%)."
    return f"{animal_label} triggered {rule['rule_name']}."


def log_event_to_mongodb(
    mongo_db: Database | None,
    *,
    event: dict[str, Any],
    rule: dict[str, Any],
    alert: dict[str, Any],
) -> None:
    if mongo_db is None:
        return
    collection_name = _collection_for_event(str(event["event_type"]))
    document = {
        "event_type": event["event_type"],
        "animal_id": event["animal_id"],
        "zone_id": event.get("zone_id"),
        "timestamp": event.get("timestamp") or datetime.utcnow(),
        "severity": rule.get("severity"),
        "rule_id": rule.get("rule_id"),
        "alert_id": alert.get("alert_id"),
        "observation_id": event.get("observation_id"),
        "metadata": {
            "source": "phase_5_eca",
            "previous_zone_id": event.get("previous_zone_id"),
            "battery_level": event.get("battery_level"),
            "location": {"lat": event.get("latitude"), "lng": event.get("longitude")},
        },
    }
    try:
        mongo_db[collection_name].insert_one(document)
    except Exception as exc:
        logger.warning("MongoDB event logging failed for alert %s: %s", alert.get("alert_id"), exc)


def _collection_for_event(event_type: str) -> str:
    if event_type == "low_battery":
        return "device_events"
    if event_type in {"zone_entry", "zone_exit", "restricted_zone_entry", "protected_zone_entry", "high_risk_zone_entry"}:
        return "boundary_events"
    return "wildlife_events"


def _normalize(value: Any) -> str:
    return str(value or "").strip().lower()


def _as_float(value: Any) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None
