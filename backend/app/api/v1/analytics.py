"""Operational aggregates computed from stored PostgreSQL/PostGIS records."""
from datetime import datetime, timedelta, timezone
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import text
from sqlalchemy.orm import Session
from backend.app.db.postgres.session import get_postgres_session

router = APIRouter(prefix="/analytics", tags=["analytics"])


@router.get("")
def analytics(
    start_time: datetime | None = None,
    end_time: datetime | None = None,
    species_filter: str | None = Query(None, alias="species", pattern="^(elephant|tiger|deer)$"),
    session: Session = Depends(get_postgres_session),
):
    end = end_time or datetime.now(timezone.utc)
    start = start_time or end - timedelta(days=7)
    if start.tzinfo is None or end.tzinfo is None:
        raise HTTPException(400, "Use timestamps with a timezone")
    if start >= end or end - start > timedelta(days=366):
        raise HTTPException(400, "Choose an increasing time range of at most 366 days")
    params = {"start": start, "end": end, "species": species_filter}
    conn = session.connection()
    # All dashboard aggregates use one consistent snapshot.
    conn.execute(text("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ, READ ONLY"))
    summary = dict(conn.execute(text("""
        SELECT count(*) AS total,
               count(*) FILTER (WHERE al.alert_type LIKE '%zone%') AS violations
        FROM alerts al JOIN animals a USING(animal_id)
        WHERE al.created_at >= :start AND al.created_at < :end
          AND (CAST(:species AS varchar) IS NULL OR a.species = :species)
    """), params).mappings().one())
    active = conn.execute(text("""
        SELECT count(*) FROM animals
        WHERE status = 'active' AND (CAST(:species AS varchar) IS NULL OR species = :species)
    """), params).scalar_one()
    hourly = conn.execute(text("""
        SELECT extract(hour FROM o.observed_at AT TIME ZONE 'UTC')::int AS hour,
               count(*) FILTER (WHERE a.species = 'elephant') AS elephants,
               count(*) FILTER (WHERE a.species = 'tiger') AS tigers,
               count(*) FILTER (WHERE a.species = 'deer') AS deer
        FROM observations o JOIN animals a USING(animal_id)
        WHERE o.observed_at >= :start AND o.observed_at < :end
          AND (CAST(:species AS varchar) IS NULL OR a.species = :species)
        GROUP BY 1 ORDER BY 1
    """), params).mappings().all()
    by_hour = {row["hour"]: dict(row) for row in hourly}
    hours = [dict(by_hour.get(hour, {"elephants": 0, "tigers": 0, "deer": 0}), hour=f"{hour:02d}") for hour in range(24)]
    trend = [dict(row) for row in conn.execute(text("""
        WITH days AS (
            SELECT generate_series(
                CAST(CAST(:start AS timestamptz) AT TIME ZONE 'UTC' AS date),
                (CAST(CAST(:end AS timestamptz) AT TIME ZONE 'UTC' AS date) - interval '1 day')::date,
                interval '1 day'
            )::date AS day
        ), daily AS (
            SELECT (al.created_at AT TIME ZONE 'UTC')::date AS day,
                   count(*) FILTER (WHERE al.severity = 'info') AS info,
                   count(*) FILTER (WHERE al.severity = 'low') AS low,
                   count(*) FILTER (WHERE al.severity = 'medium') AS medium,
                   count(*) FILTER (WHERE al.severity = 'high') AS high,
                   count(*) FILTER (WHERE al.severity = 'critical') AS critical
            FROM alerts al JOIN animals a USING(animal_id)
            WHERE al.created_at >= :start AND al.created_at < :end
              AND (CAST(:species AS varchar) IS NULL OR a.species = :species)
            GROUP BY 1
        )
        SELECT to_char(days.day, 'YYYY-MM-DD') AS day,
               coalesce(daily.info, 0) AS info, coalesce(daily.low, 0) AS low,
               coalesce(daily.medium, 0) AS medium, coalesce(daily.high, 0) AS high,
               coalesce(daily.critical, 0) AS critical
        FROM days LEFT JOIN daily USING(day) ORDER BY days.day
    """), params).mappings()]
    species_activity = [dict(row) for row in conn.execute(text("""
        SELECT initcap(a.species) AS name, count(*) AS value
        FROM observations o JOIN animals a USING(animal_id)
        WHERE observed_at >= :start AND observed_at < :end
          AND (CAST(:species AS varchar) IS NULL OR a.species = :species)
        GROUP BY a.species ORDER BY a.species
    """), params).mappings()]
    distance = conn.execute(text("""
        WITH points AS (
            SELECT o.animal_id, o.observed_at, o.location,
                   lag(o.location) OVER (PARTITION BY o.animal_id ORDER BY o.observed_at, o.observation_id) previous,
                   lag(o.observed_at) OVER (PARTITION BY o.animal_id ORDER BY o.observed_at, o.observation_id) previous_at
            FROM observations o JOIN animals a USING(animal_id)
            WHERE o.observed_at >= :start - interval '30 minutes' AND o.observed_at < :end
              AND (CAST(:species AS varchar) IS NULL OR a.species = :species)
        ), totals AS (
            SELECT animal_id, sum(ST_Distance(location::geography, previous::geography)) meters
            FROM points
            WHERE observed_at >= :start AND previous IS NOT NULL
              AND observed_at - previous_at <= interval '30 minutes'
            GROUP BY animal_id
        ) SELECT coalesce(avg(coalesce(meters,0)),0) / 1000.0 FROM totals
    """), params).scalar_one()
    zone_time = [dict(name=row["name"], value=round(float(row["value"]), 2)) for row in conn.execute(text("""
        WITH intervals AS (
            SELECT o.animal_id, o.location, o.observed_at,
                   lead(o.observed_at) OVER (PARTITION BY o.animal_id ORDER BY o.observed_at, o.observation_id) next_at
            FROM observations o JOIN animals a USING(animal_id)
            WHERE o.observed_at >= :start - interval '30 minutes' AND o.observed_at < :end
              AND (CAST(:species AS varchar) IS NULL OR a.species = :species)
        ), clipped AS (
            SELECT location, observed_at,
                   greatest(observed_at, :start) AS interval_start,
                   least(next_at, :end) AS interval_end
            FROM intervals
            WHERE next_at > :start AND next_at > observed_at
              AND next_at - observed_at <= interval '30 minutes'
        )
        SELECT coalesce(z.zone_type, 'unclassified') AS name,
               sum(extract(epoch FROM (i.interval_end - i.interval_start))) / 3600.0 AS value
        FROM clipped i
        LEFT JOIN LATERAL (
            SELECT zone_type FROM zone_versions
            WHERE valid_from <= i.observed_at AND (valid_to IS NULL OR i.observed_at < valid_to)
              AND ST_Covers(geometry, i.location)
            ORDER BY CASE risk_level WHEN 'critical' THEN 0 WHEN 'high' THEN 1 WHEN 'medium' THEN 2 ELSE 3 END,
                     ST_Area(geometry), zone_id LIMIT 1
        ) z ON true
        WHERE i.interval_end > i.interval_start
        GROUP BY z.zone_type ORDER BY value DESC
    """), params).mappings()]
    peak = max(hours, key=lambda row: row["elephants"] + row["tigers"] + row["deer"])
    return {
        "metrics": [
            {"key": "total-alerts", "label": "Alerts in range", "value": summary["total"]},
            {"key": "zone-violations", "label": "Zone alerts", "value": summary["violations"]},
            {"key": "active-animals", "label": "Active animals now", "value": active},
            {"key": "avg-distance", "label": "Avg. distance per moving animal", "value": round(float(distance), 2), "unit": "km"},
            {"key": "peak-hour", "label": "Peak observation hour (UTC)", "value": peak["hour"] + ":00" if species_activity else "—"},
        ],
        "hourlyActivity": hours,
        "alertTrend": trend,
        "speciesActivity": species_activity,
        "zoneTime": zone_time,
        "source": "PostgreSQL / PostGIS",
        "generated_at": datetime.now(timezone.utc),
        "start_time": start,
        "end_time": end,
        "note": "Activity counts are GPS observations. Distance and dwell use consecutive fixes at most 30 minutes apart. Dwell is clipped to the selected range and uses the zone version active at the first fix; zone time is estimated in hours.",
    }
