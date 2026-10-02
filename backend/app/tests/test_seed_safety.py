"""Check seed behavior with mocks, without connecting to any database."""
import unittest
from unittest.mock import MagicMock, patch
from backend.app.seed.postgres_seed import seed_postgres
from backend.app.seed.mongodb_seed import seed_mongodb, EVENTS


class SeedSafetyTest(unittest.TestCase):
    def test_postgres_only_inserts_missing_rows(self):
        engine = MagicMock()
        conn = engine.begin.return_value.__enter__.return_value
        with patch("backend.app.seed.postgres_seed.create_engine", return_value=engine):
            seed_postgres()
        statements = [str(call.args[0]).upper() for call in conn.execute.call_args_list]
        self.assertGreater(len(statements), 0)
        for statement in statements:
            self.assertTrue(statement.strip().startswith("INSERT INTO"), statement)
            self.assertIn("ON CONFLICT DO NOTHING", statement)

    def test_mongo_preserves_existing_documents(self):
        client = MagicMock()
        db = MagicMock()
        with patch("backend.app.seed.mongodb_seed.get_mongo_client", return_value=client), patch(
            "backend.app.seed.mongodb_seed.get_mongo_database", return_value=db
        ), patch("backend.app.seed.mongodb_seed.find_forbidden_core_collections", return_value=[]), patch(
            "backend.app.seed.mongodb_seed.ensure_event_indexes"
        ):
            seed_mongodb()
        collection = db.__getitem__.return_value
        collection.delete_many.assert_not_called()
        collection.drop.assert_not_called()
        self.assertEqual(collection.update_one.call_count, sum(map(len, EVENTS.values())))
        for call in collection.update_one.call_args_list:
            self.assertEqual(set(call.args[1]), {"$setOnInsert"})
            self.assertTrue(call.kwargs["upsert"])
