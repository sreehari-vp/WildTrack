from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import create_engine, text

from backend.app.core.config import get_settings


def utc(value: str) -> datetime:
    return datetime.fromisoformat(value).replace(tzinfo=timezone.utc)


FOREST_BOUNDARY_WKT = (
    "POLYGON((76.612 11.354,76.735 11.362,76.762 11.424,76.726 11.486,"
    "76.620 11.470,76.584 11.409,76.612 11.354))"
)

ZONES = [
    ("ZONE-SAFE", "North Bamboo Safe Zone", "safe", "safe", "Open bamboo and grazing flats used by elephant herds.", "POLYGON((76.626 11.432,76.673 11.433,76.670 11.468,76.621 11.462,76.626 11.432))"),
    ("ZONE-BUFFER", "Theppakadu Buffer Zone", "buffer", "medium", "Patrolled buffer near camp roads and grazing routes.", "POLYGON((76.671 11.431,76.715 11.430,76.727 11.462,76.670 11.468,76.671 11.431))"),
    ("ZONE-RESTRICTED", "Kargudi Restricted Zone", "restricted", "high", "Narrow movement corridor under road-crossing watch.", "POLYGON((76.624 11.398,76.674 11.399,76.673 11.432,76.626 11.432,76.624 11.398))"),
    ("ZONE-HIGH-RISK", "Moyar Ridge High-Risk Zone", "high-risk", "critical", "Steep terrain with repeated conflict reports.", "POLYGON((76.674 11.398,76.733 11.397,76.715 11.430,76.673 11.432,76.674 11.398))"),
    ("ZONE-WATER", "Avarahalla Water Source Zone", "water-source", "info", "Seasonal water line used by deer and elephants.", "POLYGON((76.612 11.372,76.652 11.371,76.674 11.399,76.624 11.398,76.612 11.372))"),
    ("ZONE-PROTECTED", "Sand Road Protected Zone", "protected", "high", "Protected habitat with tiger activity.", "POLYGON((76.652 11.371,76.725 11.368,76.733 11.397,76.674 11.398,76.652 11.371))"),
]

DEVICES = [
    ("DEV-E-001", "WT-E-001", "gps_collar", "online", 86, utc("2026-09-24T10:12:00")),
    ("DEV-E-002", "WT-E-002", "gps_collar", "online", 78, utc("2026-09-24T10:11:00")),
    ("DEV-T-001", "WT-T-001", "gps_collar", "online", 72, utc("2026-09-24T10:10:00")),
    ("DEV-T-002", "WT-T-002", "gps_collar", "online", 64, utc("2026-09-24T10:09:00")),
    ("DEV-D-001", "WT-D-001", "gps_tag", "online", 92, utc("2026-09-24T10:12:00")),
    ("DEV-D-002", "WT-D-002", "gps_tag", "online", 58, utc("2026-09-24T10:08:00")),
    ("DEV-D-003", "WT-D-003", "gps_tag", "low_battery", 18, utc("2026-09-24T10:05:00")),
    ("DEV-E-003", "WT-E-003", "gps_collar", "online", 83, utc("2026-10-01T10:15:00")),
    ("DEV-E-004", "WT-E-004", "gps_collar", "online", 69, utc("2026-10-01T10:14:00")),
    ("DEV-E-005", "WT-E-005", "gps_collar", "online", 77, utc("2026-10-01T10:13:00")),
    ("DEV-E-006", "WT-E-006", "gps_collar", "online", 61, utc("2026-10-01T10:12:00")),
    ("DEV-T-003", "WT-T-003", "gps_collar", "online", 88, utc("2026-10-01T10:11:00")),
    ("DEV-T-004", "WT-T-004", "gps_collar", "online", 73, utc("2026-10-01T10:10:00")),
    ("DEV-T-005", "WT-T-005", "gps_collar", "online", 55, utc("2026-10-01T10:09:00")),
    ("DEV-T-006", "WT-T-006", "gps_collar", "low_battery", 22, utc("2026-10-01T10:08:00")),
    ("DEV-D-004", "WT-D-004", "gps_tag", "online", 94, utc("2026-10-01T10:07:00")),
    ("DEV-D-005", "WT-D-005", "gps_tag", "online", 81, utc("2026-10-01T10:06:00")),
    ("DEV-D-006", "WT-D-006", "gps_tag", "online", 67, utc("2026-10-01T10:05:00")),
    ("DEV-D-007", "WT-D-007", "gps_tag", "online", 74, utc("2026-10-01T10:04:00")),
]

ANIMALS = [
    ("EL-001", "EL-001", "elephant", "Muthu", 31, "male", "active", "DEV-E-001"),
    ("EL-002", "EL-002", "elephant", "Kaveri", 28, "female", "active", "DEV-E-002"),
    ("TG-001", "TG-001", "tiger", "Stripe 17", 7, "male", "active", "DEV-T-001"),
    ("TG-002", "TG-002", "tiger", "Moyar Male", 9, "male", "idle", "DEV-T-002"),
    ("DR-001", "DR-001", "deer", "Dawn Group 1", 4, "female", "active", "DEV-D-001"),
    ("DR-002", "DR-002", "deer", "Spotted Doe", 5, "female", "active", "DEV-D-002"),
    ("DR-003", "DR-003", "deer", "Glen Slope Group", 3, "unknown", "offline", "DEV-D-003"),
    ("EL-003", "EL-003", "elephant", "Meera", 24, "female", "active", "DEV-E-003"),
    ("EL-004", "EL-004", "elephant", "Rajan", 36, "male", "active", "DEV-E-004"),
    ("EL-005", "EL-005", "elephant", "Nila", 18, "female", "active", "DEV-E-005"),
    ("EL-006", "EL-006", "elephant", "Kannan", 42, "male", "idle", "DEV-E-006"),
    ("TG-003", "TG-003", "tiger", "Fern Female", 6, "female", "active", "DEV-T-003"),
    ("TG-004", "TG-004", "tiger", "Kargudi Male", 8, "male", "active", "DEV-T-004"),
    ("TG-005", "TG-005", "tiger", "Ridge Female", 5, "female", "active", "DEV-T-005"),
    ("TG-006", "TG-006", "tiger", "Sand Road Male", 10, "male", "idle", "DEV-T-006"),
    ("DR-004", "DR-004", "deer", "Bamboo Herd", 4, "unknown", "active", "DEV-D-004"),
    ("DR-005", "DR-005", "deer", "Moyar Doe", 3, "female", "active", "DEV-D-005"),
    ("DR-006", "DR-006", "deer", "Waterline Herd", 5, "unknown", "active", "DEV-D-006"),
    ("DR-007", "DR-007", "deer", "Teak Slope Stag", 6, "male", "active", "DEV-D-007"),
]

OBSERVATIONS = [
    ("OBS-001", "EL-001", "DEV-E-001", 11.451000, 76.644000, 3.2, utc("2026-09-24T10:12:00")),
    ("OBS-002", "EL-002", "DEV-E-002", 11.414000, 76.651000, 4.8, utc("2026-09-24T10:11:00")),
    ("OBS-003", "TG-001", "DEV-T-001", 11.383000, 76.692000, 6.3, utc("2026-09-24T10:10:00")),
    ("OBS-004", "TG-002", "DEV-T-002", 11.412000, 76.704000, 0.9, utc("2026-09-24T10:09:00")),
    ("OBS-005", "DR-001", "DEV-D-001", 11.444000, 76.633000, 4.2, utc("2026-09-24T10:12:00")),
    ("OBS-006", "DR-002", "DEV-D-002", 11.392000, 76.654000, 3.9, utc("2026-09-24T10:08:00")),
    ("OBS-007", "DR-003", "DEV-D-003", 11.388000, 76.714000, 0.0, utc("2026-09-24T10:05:00")),
    ("OBS-008", "EL-002", "DEV-E-002", 11.410000, 76.647000, 4.4, utc("2026-09-24T09:50:00")),
    ("OBS-009", "TG-001", "DEV-T-001", 11.381000, 76.685000, 5.7, utc("2026-09-24T09:45:00")),
    ("OBS-010", "EL-003", "DEV-E-003", 11.456000, 76.657000, 2.8, utc("2026-10-01T10:15:00")),
    ("OBS-011", "EL-004", "DEV-E-004", 11.447000, 76.694000, 1.6, utc("2026-10-01T10:14:00")),
    ("OBS-012", "EL-005", "DEV-E-005", 11.419000, 76.638000, 3.7, utc("2026-10-01T10:13:00")),
    ("OBS-013", "EL-006", "DEV-E-006", 11.407000, 76.683000, 0.4, utc("2026-10-01T10:12:00")),
    ("OBS-014", "TG-003", "DEV-T-003", 11.379000, 76.671000, 7.2, utc("2026-10-01T10:11:00")),
    ("OBS-015", "TG-004", "DEV-T-004", 11.402000, 76.716000, 5.9, utc("2026-10-01T10:10:00")),
    ("OBS-016", "TG-005", "DEV-T-005", 11.423000, 76.697000, 4.6, utc("2026-10-01T10:09:00")),
    ("OBS-017", "TG-006", "DEV-T-006", 11.374000, 76.704000, 0.7, utc("2026-10-01T10:08:00")),
    ("OBS-018", "DR-004", "DEV-D-004", 11.459000, 76.632000, 4.8, utc("2026-10-01T10:07:00")),
    ("OBS-019", "DR-005", "DEV-D-005", 11.433000, 76.682000, 6.1, utc("2026-10-01T10:06:00")),
    ("OBS-020", "DR-006", "DEV-D-006", 11.381000, 76.631000, 5.3, utc("2026-10-01T10:05:00")),
    ("OBS-021", "DR-007", "DEV-D-007", 11.390000, 76.701000, 3.5, utc("2026-10-01T10:04:00")),
]

ECA_RULES = [
    ("RULE-001", "Restricted zone entry", "restricted_zone_entry", '{"zone_type":"restricted"}', '{"create_alert":true}', "high", True),
    ("RULE-002", "Protected zone tiger presence", "protected_zone_entry", '{"zone_type":"protected","species":"tiger"}', '{"create_alert":true}', "high", True),
    ("RULE-003", "Low battery warning", "low_battery", '{"battery_level_lt":25}', '{"create_alert":true}', "medium", True),
    ("RULE-004", "High-risk zone entry", "high_risk_zone_entry", '{"risk_level":"critical"}', '{"create_alert":true}', "critical", True),
]

ALERTS = [
    ("ALT-001", "EL-002", "ZONE-RESTRICTED", "RULE-001", "restricted_zone_entry", "high", "Kaveri entered Kargudi Restricted Zone.", "open", None),
    ("ALT-002", "TG-001", "ZONE-PROTECTED", "RULE-002", "protected_zone_entry", "high", "Stripe 17 is moving inside Sand Road Protected Zone.", "acknowledged", None),
    ("ALT-003", "DR-003", "ZONE-PROTECTED", "RULE-003", "low_battery", "medium", "Glen Slope Group tracker battery is below threshold.", "open", None),
]


def seed_postgres() -> None:
    settings = get_settings()
    engine = create_engine(settings.sqlalchemy_migration_url, pool_pre_ping=True)
    with engine.begin() as conn:

        conn.execute(
            text(
                """
                INSERT INTO forest_boundaries (boundary_id, boundary_name, description, geometry)
                VALUES ('BOUNDARY-NILGIRI', 'Nilgiri Ridge Wildlife Reserve',
                        'Demonstration monitoring boundary in the Nilgiri region.',
                        ST_Multi(ST_GeomFromText(:wkt, 4326)))
                ON CONFLICT DO NOTHING
                """
            ),
            {"wkt": FOREST_BOUNDARY_WKT},
        )

        for zone in ZONES:
            conn.execute(
                text(
                    """
                    INSERT INTO zones (zone_id, zone_name, zone_type, risk_level, description, geometry)
                    VALUES (:zone_id, :zone_name, :zone_type, :risk_level, :description,
                            ST_Multi(ST_GeomFromText(:wkt, 4326)))
                ON CONFLICT DO NOTHING
                    """
                ),
                {
                    "zone_id": zone[0],
                    "zone_name": zone[1],
                    "zone_type": zone[2],
                    "risk_level": zone[3],
                    "description": zone[4],
                    "wkt": zone[5],
                },
            )

        conn.execute(
            text(
                """
                INSERT INTO devices (device_id, device_code, device_type, status, battery_level, last_seen)
                VALUES (:device_id, :device_code, :device_type, :status, :battery_level, :last_seen)
                ON CONFLICT DO NOTHING
                """
            ),
            [dict(zip(("device_id", "device_code", "device_type", "status", "battery_level", "last_seen"), row)) for row in DEVICES],
        )
        conn.execute(
            text(
                """
                INSERT INTO animals (animal_id, animal_code, species, name, age, sex, status, device_id)
                VALUES (:animal_id, :animal_code, :species, :name, :age, :sex, :status, :device_id)
                ON CONFLICT DO NOTHING
                """
            ),
            [dict(zip(("animal_id", "animal_code", "species", "name", "age", "sex", "status", "device_id"), row)) for row in ANIMALS],
        )

        for observation in OBSERVATIONS:
            conn.execute(
                text(
                    """
                    INSERT INTO observations
                    (observation_id, animal_id, device_id, latitude, longitude, speed, observed_at, location)
                    VALUES (:observation_id, :animal_id, :device_id, :latitude, :longitude, :speed,
                            :observed_at, ST_SetSRID(ST_MakePoint(:longitude, :latitude), 4326))
                ON CONFLICT DO NOTHING
                    """
                ),
                dict(zip(("observation_id", "animal_id", "device_id", "latitude", "longitude", "speed", "observed_at"), observation)),
            )

        conn.execute(
            text(
                """
                INSERT INTO eca_rules (rule_id, rule_name, event_type, condition, action, severity, enabled)
                VALUES (:rule_id, :rule_name, :event_type, CAST(:condition AS jsonb),
                        CAST(:action AS jsonb), :severity, :enabled)
                ON CONFLICT DO NOTHING
                """
            ),
            [dict(zip(("rule_id", "rule_name", "event_type", "condition", "action", "severity", "enabled"), row)) for row in ECA_RULES],
        )
        conn.execute(
            text(
                """
                INSERT INTO alerts
                (alert_id, animal_id, zone_id, rule_id, alert_type, severity, message, status, resolved_at)
                VALUES (:alert_id, :animal_id, :zone_id, :rule_id, :alert_type, :severity, :message, :status, :resolved_at)
                ON CONFLICT DO NOTHING
                """
            ),
            [dict(zip(("alert_id", "animal_id", "zone_id", "rule_id", "alert_type", "severity", "message", "status", "resolved_at"), row)) for row in ALERTS],
        )


if __name__ == "__main__":
    seed_postgres()
    print("PostgreSQL seed complete.")
