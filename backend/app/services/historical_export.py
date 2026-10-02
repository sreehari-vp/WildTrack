"""Resumable PostgreSQL-to-Parquet exports for the local historical archive.

Source rows are immutable facts. A PostgreSQL ledger claims each ID once; pending
batches retain their ID and filename across retries, so a crash cannot create
duplicate archived rows on the next run.
"""

from __future__ import annotations

import hashlib
import json
import os
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

import pyarrow as pa
import pyarrow.parquet as pq
from sqlalchemy import text
from sqlalchemy.engine import Connection

from backend.app.db.postgres.session import engine


DATASETS = ("observations", "alerts")
LOCK_KEY = "wildtrack-historical-export"

SCHEMAS = {
    "observations": pa.schema([
        ("observation_id", pa.string()), ("animal_id", pa.string()),
        ("animal_code", pa.string()), ("species", pa.string()),
        ("device_id", pa.string()), ("latitude", pa.float64()),
        ("longitude", pa.float64()), ("speed_kmh", pa.float64()),
        ("zone_id", pa.string()), ("zone_version", pa.int32()),
        ("event_time", pa.timestamp("us", tz="UTC")),
    ]),
    "alerts": pa.schema([
        ("alert_id", pa.string()), ("animal_id", pa.string()),
        ("animal_code", pa.string()), ("species", pa.string()),
        ("zone_id", pa.string()), ("rule_id", pa.string()),
        ("rule_version", pa.int32()), ("alert_type", pa.string()),
        ("severity", pa.string()), ("message", pa.string()),
        ("event_time", pa.timestamp("us", tz="UTC")),
    ]),
}

CLAIM_SQL = {
    "observations": """
        SELECT o.observation_id AS source_id FROM observations o
        WHERE NOT EXISTS (
            SELECT 1 FROM historical_export_items i
            WHERE i.dataset='observations' AND i.source_id=o.observation_id
        )
        ORDER BY o.observed_at, o.observation_id LIMIT :limit
        FOR UPDATE OF o SKIP LOCKED
    """,
    "alerts": """
        SELECT a.alert_id AS source_id FROM alerts a
        WHERE NOT EXISTS (
            SELECT 1 FROM historical_export_items i
            WHERE i.dataset='alerts' AND i.source_id=a.alert_id
        )
        ORDER BY a.created_at, a.alert_id LIMIT :limit
        FOR UPDATE OF a SKIP LOCKED
    """,
}

SOURCE_SQL = {
    "observations": """
        SELECT o.observation_id, o.animal_id, a.animal_code, a.species,
               o.device_id, o.latitude::float8 AS latitude,
               o.longitude::float8 AS longitude, o.speed::float8 AS speed_kmh,
               z.zone_id, z.version_no AS zone_version,
               o.observed_at AS event_time
        FROM historical_export_items i
        JOIN observations o ON o.observation_id=i.source_id
        JOIN animals a ON a.animal_id=o.animal_id
        LEFT JOIN LATERAL (
            SELECT zv.zone_id, zv.version_no FROM zone_versions zv
            WHERE zv.valid_from <= o.observed_at
              AND (zv.valid_to IS NULL OR o.observed_at < zv.valid_to)
              AND ST_Covers(zv.geometry, o.location)
            ORDER BY CASE zv.risk_level WHEN 'critical' THEN 0 WHEN 'high' THEN 1
                     WHEN 'medium' THEN 2 ELSE 3 END,
                     ST_Area(zv.geometry), zv.zone_id LIMIT 1
        ) z ON true
        WHERE i.batch_id=:batch_id AND i.dataset='observations'
        ORDER BY o.observed_at, o.observation_id
    """,
    "alerts": """
        SELECT al.alert_id, al.animal_id, a.animal_code, a.species,
               al.zone_id, al.rule_id, al.rule_version, al.alert_type,
               al.severity, al.message, al.created_at AS event_time
        FROM historical_export_items i
        JOIN alerts al ON al.alert_id=i.source_id
        JOIN animals a ON a.animal_id=al.animal_id
        WHERE i.batch_id=:batch_id AND i.dataset='alerts'
        ORDER BY al.created_at, al.alert_id
    """,
}


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _claim_batch(conn: Connection, dataset: str, output_root: Path, limit: int) -> str | None:
    with conn.begin():
        pending = conn.execute(text("""
            SELECT batch_id, output_root FROM historical_export_batches
            WHERE dataset=:dataset AND status='preparing'
            ORDER BY created_at, batch_id LIMIT 1 FOR UPDATE
        """), {"dataset": dataset}).mappings().first()
        if pending:
            if Path(pending["output_root"]).resolve() != output_root:
                raise ValueError(f"Pending {dataset} batch uses {pending['output_root']}; resume with that output directory")
            return pending["batch_id"]

        ids = [row["source_id"] for row in conn.execute(text(CLAIM_SQL[dataset]), {"limit": limit}).mappings()]
        if not ids:
            return None
        batch_id = str(uuid4())
        conn.execute(text("""
            INSERT INTO historical_export_batches(batch_id, dataset, output_root, status, row_count)
            VALUES (:batch_id, :dataset, :output_root, 'preparing', :row_count)
        """), {"batch_id": batch_id, "dataset": dataset, "output_root": str(output_root), "row_count": len(ids)})
        conn.execute(text("""
            INSERT INTO historical_export_items(dataset, source_id, batch_id)
            SELECT :dataset, source_id, :batch_id FROM unnest(CAST(:ids AS text[])) AS source_ids(source_id)
        """), {"dataset": dataset, "batch_id": batch_id, "ids": ids})
        return batch_id


def write_parquet_files(dataset: str, batch_id: str, rows: list[dict], output_root: Path) -> list[dict]:
    by_day: dict[str, list[dict]] = defaultdict(list)
    for row in rows:
        when = row["event_time"]
        if when.tzinfo is None:
            raise ValueError("Historical timestamps must include a timezone")
        by_day[when.astimezone(timezone.utc).date().isoformat()].append(row)

    files = []
    for day, partition_rows in sorted(by_day.items()):
        relative = Path(dataset) / f"event_date={day}" / f"part-{batch_id}.parquet"
        target = output_root / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        temporary = target.with_suffix(".parquet.tmp")
        table = pa.Table.from_pylist(partition_rows, schema=SCHEMAS[dataset])
        try:
            pq.write_table(table, temporary, compression="snappy")
            if pq.ParquetFile(temporary).metadata.num_rows != len(partition_rows):
                raise RuntimeError(f"Parquet row count mismatch for {temporary}")
            os.replace(temporary, target)
        finally:
            temporary.unlink(missing_ok=True)
        files.append({"relative_path": relative.as_posix(), "rows": len(partition_rows), "sha256": _sha256(target)})
    return files


def _write_batch(conn: Connection, dataset: str, batch_id: str, output_root: Path) -> dict:
    # Read one consistent snapshot; a source row deleted after claim leaves the
    # batch pending for investigation rather than silently omitting a fact.
    with conn.begin():
        conn.execute(text("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ, READ ONLY"))
        expected = conn.execute(text("""
            SELECT count(*) FROM historical_export_items WHERE batch_id=:batch_id
        """), {"batch_id": batch_id}).scalar_one()
        rows = [dict(row) for row in conn.execute(text(SOURCE_SQL[dataset]), {"batch_id": batch_id}).mappings()]
    if len(rows) != expected:
        raise RuntimeError(f"Batch {batch_id} has {expected} claimed IDs but {len(rows)} source rows")

    files = write_parquet_files(dataset, batch_id, rows, output_root)

    with conn.begin():
        conn.execute(text("""
            UPDATE historical_export_batches
            SET status='ready', row_count=:row_count, files=CAST(:files AS jsonb), completed_at=clock_timestamp()
            WHERE batch_id=:batch_id AND status='preparing'
        """), {"batch_id": batch_id, "row_count": len(rows), "files": json.dumps(files)})
    return {"batch_id": batch_id, "dataset": dataset, "row_count": len(rows), "files": files}


def export_incremental(output_dir: Path, *, batch_size: int = 1000, max_batches: int = 100) -> list[dict]:
    if not 1 <= batch_size <= 10000:
        raise ValueError("batch_size must be between 1 and 10000")
    if max_batches < 1:
        raise ValueError("max_batches must be positive")
    output_root = output_dir.resolve()
    output_root.mkdir(parents=True, exist_ok=True)
    results = []
    with engine.connect() as conn:
        acquired = conn.execute(text("SELECT pg_try_advisory_lock(hashtext(:key))"), {"key": LOCK_KEY}).scalar_one()
        conn.commit()
        if not acquired:
            raise RuntimeError("Another historical export is running")
        try:
            for dataset in DATASETS:
                batches = 0
                while batches < max_batches:
                    batch_id = _claim_batch(conn, dataset, output_root, batch_size)
                    if batch_id is None:
                        break
                    results.append(_write_batch(conn, dataset, batch_id, output_root))
                    batches += 1
        finally:
            conn.execute(text("SELECT pg_advisory_unlock(hashtext(:key))"), {"key": LOCK_KEY})
            conn.commit()
    return results


def export_status() -> list[dict]:
    with engine.connect() as conn:
        return [dict(row) for row in conn.execute(text("""
            SELECT dataset, status, count(*) AS batches, sum(row_count)::bigint AS rows
            FROM historical_export_batches GROUP BY dataset, status ORDER BY dataset, status
        """)).mappings()]


def verify_export_files() -> list[str]:
    errors = []
    with engine.connect() as conn:
        batches = [dict(row) for row in conn.execute(text("""
            SELECT batch_id, output_root, row_count, files FROM historical_export_batches
            WHERE status='ready' ORDER BY created_at
        """)).mappings()]
    for batch in batches:
        seen = 0
        for item in batch["files"]:
            path = Path(batch["output_root"]) / item["relative_path"]
            if not path.is_file():
                errors.append(f"Missing {path}")
                continue
            if _sha256(path) != item["sha256"]:
                errors.append(f"Checksum mismatch {path}")
            actual_rows = pq.ParquetFile(path).metadata.num_rows
            if actual_rows != item["rows"]:
                errors.append(f"Row count mismatch {path}")
            seen += actual_rows
        if seen != batch["row_count"]:
            errors.append(f"Batch {batch['batch_id']} row count mismatch")
    return errors


