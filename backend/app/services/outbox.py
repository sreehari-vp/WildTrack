"""Transactional PostgreSQL outbox with idempotent MongoDB delivery."""

from __future__ import annotations

import asyncio
import json
import logging
from datetime import datetime
from typing import Any
from uuid import uuid4

from pymongo.database import Database
from sqlalchemy import text
from sqlalchemy.engine import Connection

from backend.app.db.mongodb.client import (
    EVENT_COLLECTIONS, ensure_event_indexes, find_forbidden_core_collections,
    get_mongo_client, get_mongo_database,
)
from backend.app.db.postgres.session import engine

logger = logging.getLogger(__name__)


def enqueue_event(conn: Connection, collection: str, payload: dict[str, Any]) -> str:
    """Call inside the same PostgreSQL transaction as the observation or alert."""
    if collection not in EVENT_COLLECTIONS:
        raise ValueError("Unknown event collection")
    event_id = str(uuid4())
    conn.execute(text("""
        INSERT INTO event_outbox (event_id, collection_name, payload)
        VALUES (:event_id, :collection, CAST(:payload AS jsonb))
    """), {
        "event_id": event_id,
        "collection": collection,
        "payload": json.dumps(payload, default=lambda value: value.isoformat() if isinstance(value, datetime) else str(value)),
    })
    return event_id


def _mongo_document(row: dict[str, Any]) -> dict[str, Any]:
    document = dict(row["payload"])
    timestamp = document.get("timestamp")
    if isinstance(timestamp, str):
        document["timestamp"] = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
    document["event_id"] = row["event_id"]
    return document


def _record_failure(conn: Connection, event_id: str, attempts: int, error: Exception) -> None:
    delay = min(300, 2 ** min(attempts + 1, 8))
    conn.execute(text("""
        UPDATE event_outbox
        SET attempts = attempts + 1,
            next_attempt_at = now() + (:delay * interval '1 second'),
            last_error = :error
        WHERE event_id = :event_id AND delivered_at IS NULL
    """), {"event_id": event_id, "delay": delay, "error": type(error).__name__[:240]})


def deliver_outbox_batch(limit: int = 50) -> dict[str, int]:
    """Safe across workers: row locks prevent duplicate concurrent attempts."""
    delivered = failed = 0
    with engine.begin() as conn:
        rows = [dict(row) for row in conn.execute(text("""
            SELECT event_id, collection_name, payload, attempts
            FROM event_outbox
            WHERE delivered_at IS NULL AND next_attempt_at <= now()
            ORDER BY created_at, event_id
            FOR UPDATE SKIP LOCKED
            LIMIT :limit
        """), {"limit": max(1, min(limit, 100))}).mappings()]
        if not rows:
            return {"delivered": 0, "failed": 0}
        client = None
        try:
            client = get_mongo_client()
            db: Database = get_mongo_database(client)
            forbidden = find_forbidden_core_collections(db)
            if forbidden:
                raise RuntimeError("MongoDB has core collections outside PostgreSQL")
            ensure_event_indexes(db)
            for row in rows:
                try:
                    db[row["collection_name"]].update_one(
                        {"event_id": row["event_id"]},
                        {"$setOnInsert": _mongo_document(row)},
                        upsert=True,
                    )
                    conn.execute(text("""
                        UPDATE event_outbox SET delivered_at=clock_timestamp(), last_error=NULL
                        WHERE event_id=:event_id
                    """), {"event_id": row["event_id"]})
                    delivered += 1
                except Exception as exc:
                    _record_failure(conn, row["event_id"], row["attempts"], exc)
                    failed += 1
        except Exception as exc:
            for row in rows:
                _record_failure(conn, row["event_id"], row["attempts"], exc)
                failed += 1
            logger.warning("Outbox delivery delayed: %s", type(exc).__name__)
        finally:
            if client is not None:
                client.close()
    return {"delivered": delivered, "failed": failed}


class OutboxWorker:
    def __init__(self, interval_seconds: float = 5.0):
        self.interval_seconds = interval_seconds
        self._task: asyncio.Task[None] | None = None

    async def start(self) -> None:
        if self._task is None or self._task.done():
            self._task = asyncio.create_task(self._run(), name="wildtrack-mongo-outbox")

    async def stop(self) -> None:
        if self._task is None or self._task.done():
            return
        self._task.cancel()
        try:
            await self._task
        except asyncio.CancelledError:
            pass

    async def _run(self) -> None:
        while True:
            batch = None
            try:
                batch = asyncio.create_task(asyncio.to_thread(deliver_outbox_batch))
                await asyncio.shield(batch)
            except asyncio.CancelledError:
                if batch is not None:
                    await batch
                raise
            except Exception as exc:
                logger.error("Outbox worker failed (%s); retrying", type(exc).__name__)
            await asyncio.sleep(self.interval_seconds)


outbox_worker = OutboxWorker()
