"""Integrity constraints, atomic active alerts, and database audit history."""
from alembic import op

revision = "0002_integrity"
down_revision = "0001_database_foundation"
branch_labels = None
depends_on = None

CHECKS = {
    "observations": {
        "ck_observations_speed": "speed >= 0",
        "ck_observations_location": "round(ST_X(location)::numeric, 6) = longitude AND round(ST_Y(location)::numeric, 6) = latitude",
    },
    "animals": {"ck_animals_status": "status IN ('active','idle','offline')"},
    "devices": {"ck_devices_status": "status IN ('online','offline','low_battery')"},
    "zones": {
        "ck_zones_risk": "risk_level IN ('safe','info','low','medium','high','critical')",
        "ck_zones_type": "zone_type IN ('safe','buffer','restricted','high-risk','water-source','protected')",
        "ck_zones_geometry": "ST_IsValid(geometry) AND NOT ST_IsEmpty(geometry)",
    },
    "alerts": {
        "ck_alerts_status": "status IN ('open','acknowledged','resolved')",
        "ck_alerts_severity": "severity IN ('info','low','medium','high','critical')",
        "ck_alerts_resolution": "(status = 'resolved') = (resolved_at IS NOT NULL)",
    },
    "eca_rules": {"ck_rules_severity": "severity IN ('info','low','medium','high','critical')"},
}


def upgrade():
    # Existing invalid data causes a transactional failure; no records are deleted.
    for table, checks in CHECKS.items():
        for name, expression in checks.items():
            op.create_check_constraint(name, table, expression)
    op.execute("""
        CREATE UNIQUE INDEX uq_alerts_active_condition ON alerts
        (animal_id, (COALESCE(rule_id, '')), alert_type, (COALESCE(zone_id, '')))
        WHERE status IN ('open', 'acknowledged')
    """)
    op.execute("""
        CREATE TABLE alert_status_history (
            history_id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
            alert_id varchar(32) NOT NULL,
            previous_status varchar(24),
            status varchar(24) NOT NULL,
            changed_at timestamptz NOT NULL DEFAULT clock_timestamp()
        )
    """)
    op.execute("CREATE INDEX ix_alert_status_history ON alert_status_history(alert_id, changed_at)")
    op.execute("""
        INSERT INTO alert_status_history(alert_id, status)
        SELECT alert_id, status FROM alerts
    """)
    op.execute("""
        CREATE FUNCTION record_alert_status() RETURNS trigger LANGUAGE plpgsql AS $$
        BEGIN
            IF TG_OP = 'INSERT' THEN
                INSERT INTO alert_status_history(alert_id, status) VALUES (NEW.alert_id, NEW.status);
            ELSIF OLD.status IS DISTINCT FROM NEW.status THEN
                IF OLD.status = 'resolved' OR (OLD.status = 'acknowledged' AND NEW.status = 'open') THEN
                    RAISE EXCEPTION 'Invalid alert status transition';
                END IF;
                INSERT INTO alert_status_history(alert_id, previous_status, status)
                VALUES (NEW.alert_id, OLD.status, NEW.status);
            END IF;
            RETURN NEW;
        END $$;
        CREATE TRIGGER alert_status_audit AFTER INSERT OR UPDATE ON alerts
        FOR EACH ROW EXECUTE FUNCTION record_alert_status();
    """)


def downgrade():
    op.execute("DROP TRIGGER alert_status_audit ON alerts")
    op.execute("DROP FUNCTION record_alert_status()")
    op.execute("DROP TABLE alert_status_history")
    op.drop_index("uq_alerts_active_condition", table_name="alerts")
    for table, checks in CHECKS.items():
        for name in checks:
            op.drop_constraint(name, table, type_="check")
