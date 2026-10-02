"""Read-only spatial consistency checks; does not require seed identities."""
import os
import unittest
from sqlalchemy import text
from backend.app.db.postgres.session import engine

@unittest.skipUnless(os.getenv("WILDTRACK_READONLY_CHECKS") == "1", "Read-only database checks are opt-in")
class Phase4SpatialTemporalTest(unittest.TestCase):
    def test_database_guards_are_installed(self):
        with engine.connect() as conn:
            conn.execute(text("SET TRANSACTION READ ONLY"))
            self.assertEqual(conn.execute(text("SELECT count(*) FROM pg_indexes WHERE indexname = 'uq_alerts_active_condition'")).scalar_one(), 1)
            self.assertEqual(conn.execute(text("SELECT count(*) FROM pg_trigger WHERE tgname = 'alert_status_audit' AND NOT tgisinternal")).scalar_one(), 1)
            self.assertEqual(conn.execute(text("""
                SELECT count(*) FROM (
                    SELECT animal_id, rule_id, alert_type, zone_id FROM alerts
                    WHERE status IN ('open','acknowledged')
                    GROUP BY animal_id, rule_id, alert_type, zone_id HAVING count(*) > 1
                ) duplicates
            """)).scalar_one(), 0)

    def test_valid_geometries_and_coordinates(self):
        with engine.connect() as conn:
            conn.execute(text("SET TRANSACTION READ ONLY"))
            self.assertEqual(conn.execute(text("SELECT count(*) FROM zones WHERE NOT ST_IsValid(geometry) OR ST_IsEmpty(geometry)")).scalar_one(), 0)
            self.assertEqual(conn.execute(text("SELECT count(*) FROM observations WHERE latitude NOT BETWEEN -90 AND 90 OR longitude NOT BETWEEN -180 AND 180 OR speed < 0")).scalar_one(), 0)
