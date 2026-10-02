"""Verify Parquet partitioning and retry identity without touching application DB."""

import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

import pyarrow.parquet as pq

from backend.app.services.historical_export import write_parquet_files


class HistoricalExportTest(unittest.TestCase):
    def test_observations_partition_by_utc_day_and_retry_uses_same_file(self):
        rows = [
            {
                "observation_id": "O1", "animal_id": "A1", "animal_code": "DR-001",
                "species": "deer", "device_id": "D1", "latitude": 11.1,
                "longitude": 76.1, "speed_kmh": 3.0, "zone_id": "ZONE-WATER",
                "zone_version": 1, "event_time": datetime(2026, 10, 1, 23, 59, tzinfo=timezone.utc),
            },
            {
                "observation_id": "O2", "animal_id": "A1", "animal_code": "DR-001",
                "species": "deer", "device_id": "D1", "latitude": 11.2,
                "longitude": 76.2, "speed_kmh": 4.0, "zone_id": None,
                "zone_version": None, "event_time": datetime(2026, 10, 2, 0, 1, tzinfo=timezone.utc),
            },
        ]
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            first = write_parquet_files("observations", "fixed-batch", rows, root)
            second = write_parquet_files("observations", "fixed-batch", rows, root)
            self.assertEqual(first, second)
            self.assertEqual(len(first), 2)
            self.assertEqual(len(list(root.rglob("*.parquet"))), 2)
            self.assertEqual(sum(pq.ParquetFile(root / item["relative_path"]).metadata.num_rows for item in first), 2)
            self.assertEqual({Path(item["relative_path"]).parent.name for item in first},
                             {"event_date=2026-10-01", "event_date=2026-10-02"})


if __name__ == "__main__":
    unittest.main()
