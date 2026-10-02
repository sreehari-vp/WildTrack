"""Outbox delivery checks using mocks; never writes application data."""

import unittest
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

from backend.app.services.outbox import _mongo_document, deliver_outbox_batch, enqueue_event


class OutboxTest(unittest.TestCase):
    def test_event_payload_is_serialized_for_postgres(self):
        conn = MagicMock()
        when = datetime(2026, 10, 1, 10, 0, tzinfo=timezone.utc)
        event_id = enqueue_event(conn, "boundary_events", {"timestamp": when, "animal_id": "DR-001"})
        params = conn.execute.call_args.args[1]
        self.assertEqual(params["event_id"], event_id)
        self.assertIn(when.isoformat(), params["payload"])
        with self.assertRaises(ValueError):
            enqueue_event(conn, "animals", {})

    def test_mongo_document_keeps_stable_event_identity(self):
        row = {"event_id": "fixed-id", "payload": {"timestamp": "2026-10-01T10:00:00+00:00", "animal_id": "DR-001"}}
        document = _mongo_document(row)
        self.assertEqual(document["event_id"], "fixed-id")
        self.assertEqual(document["timestamp"].tzinfo, timezone.utc)
        self.assertNotIn("event_id", row["payload"])

    def test_delivery_uses_idempotent_upsert_and_marks_committed_event(self):
        conn = MagicMock()
        conn.execute.return_value.mappings.return_value = [{
            "event_id": "fixed-id", "collection_name": "boundary_events",
            "payload": {"timestamp": "2026-10-01T10:00:00+00:00"}, "attempts": 0,
        }]
        engine = MagicMock()
        engine.begin.return_value.__enter__.return_value = conn
        client = MagicMock()
        database = MagicMock()
        with patch("backend.app.services.outbox.engine", engine), patch(
            "backend.app.services.outbox.get_mongo_client", return_value=client
        ), patch("backend.app.services.outbox.get_mongo_database", return_value=database), patch(
            "backend.app.services.outbox.find_forbidden_core_collections", return_value=[]
        ), patch("backend.app.services.outbox.ensure_event_indexes"):
            result = deliver_outbox_batch()
        self.assertEqual(result, {"delivered": 1, "failed": 0})
        database.__getitem__.return_value.update_one.assert_called_once()
        args, kwargs = database.__getitem__.return_value.update_one.call_args
        self.assertEqual(args[0], {"event_id": "fixed-id"})
        self.assertEqual(set(args[1]), {"$setOnInsert"})
        self.assertTrue(kwargs["upsert"])
        self.assertIn("delivered_at", str(conn.execute.call_args.args[0]))


if __name__ == "__main__":
    unittest.main()
