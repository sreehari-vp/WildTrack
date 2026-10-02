"""Versioned configuration, audit log, transactional event outbox and summaries."""

from alembic import op
import geoalchemy2
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0004_history_outbox"
down_revision = "0003_monitoring_state"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("zones", sa.Column("version_no", sa.Integer(), server_default="1", nullable=False))
    op.add_column("eca_rules", sa.Column("version_no", sa.Integer(), server_default="1", nullable=False))
    op.add_column("alerts", sa.Column("rule_version", sa.Integer(), nullable=True))

    op.create_table(
        "zone_versions",
        sa.Column("version_id", sa.BigInteger(), sa.Identity(), primary_key=True),
        sa.Column("zone_id", sa.String(32), nullable=False),
        sa.Column("version_no", sa.Integer(), nullable=False),
        sa.Column("valid_from", sa.DateTime(timezone=True), nullable=False),
        sa.Column("valid_to", sa.DateTime(timezone=True)),
        sa.Column("zone_name", sa.String(120), nullable=False),
        sa.Column("zone_type", sa.String(32), nullable=False),
        sa.Column("risk_level", sa.String(24), nullable=False),
        sa.Column("description", sa.Text()),
        sa.Column("geometry", geoalchemy2.Geometry("MULTIPOLYGON", srid=4326, spatial_index=False), nullable=False),
        sa.UniqueConstraint("zone_id", "version_no", name="uq_zone_versions_number"),
        sa.CheckConstraint("valid_to IS NULL OR valid_to >= valid_from", name="ck_zone_versions_range"),
    )
    op.create_index("ix_zone_versions_asof", "zone_versions", ["zone_id", "valid_from", "valid_to"])
    op.create_index("ix_zone_versions_geometry_gist", "zone_versions", ["geometry"], postgresql_using="gist")
    op.create_table(
        "eca_rule_versions",
        sa.Column("version_id", sa.BigInteger(), sa.Identity(), primary_key=True),
        sa.Column("rule_id", sa.String(32), nullable=False),
        sa.Column("version_no", sa.Integer(), nullable=False),
        sa.Column("valid_from", sa.DateTime(timezone=True), nullable=False),
        sa.Column("valid_to", sa.DateTime(timezone=True)),
        sa.Column("rule_name", sa.String(120), nullable=False),
        sa.Column("event_type", sa.String(60), nullable=False),
        sa.Column("condition", postgresql.JSONB(), nullable=False),
        sa.Column("action", postgresql.JSONB(), nullable=False),
        sa.Column("severity", sa.String(24), nullable=False),
        sa.Column("enabled", sa.Boolean(), nullable=False),
        sa.UniqueConstraint("rule_id", "version_no", name="uq_rule_versions_number"),
        sa.CheckConstraint("valid_to IS NULL OR valid_to >= valid_from", name="ck_rule_versions_range"),
    )
    op.create_index("ix_rule_versions_asof", "eca_rule_versions", ["rule_id", "valid_from", "valid_to"])
    op.create_table(
        "configuration_audit",
        sa.Column("audit_id", sa.BigInteger(), sa.Identity(), primary_key=True),
        sa.Column("entity_type", sa.String(32), nullable=False),
        sa.Column("entity_id", sa.String(36), nullable=False),
        sa.Column("operation", sa.String(8), nullable=False),
        sa.Column("before_data", postgresql.JSONB()),
        sa.Column("after_data", postgresql.JSONB()),
        sa.Column("changed_at", sa.DateTime(timezone=True), server_default=sa.text("clock_timestamp()"), nullable=False),
    )
    op.create_index("ix_configuration_audit_entity", "configuration_audit", ["entity_type", "entity_id", "changed_at"])
    op.create_table(
        "event_outbox",
        sa.Column("event_id", sa.String(36), primary_key=True),
        sa.Column("collection_name", sa.String(32), nullable=False),
        sa.Column("payload", postgresql.JSONB(), nullable=False),
        sa.Column("attempts", sa.Integer(), server_default="0", nullable=False),
        sa.Column("next_attempt_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("delivered_at", sa.DateTime(timezone=True)),
        sa.Column("last_error", sa.String(240)),
        sa.CheckConstraint("collection_name IN ('wildlife_events','boundary_events','sensor_events','device_events')", name="ck_event_outbox_collection"),
        sa.CheckConstraint("attempts >= 0", name="ck_event_outbox_attempts"),
    )
    op.create_index("ix_event_outbox_due", "event_outbox", ["next_attempt_at", "created_at"], postgresql_where=sa.text("delivered_at IS NULL"))

    # Existing records become version 1. Earlier changes cannot be reconstructed.
    op.execute("""
        INSERT INTO zone_versions
          (zone_id, version_no, valid_from, zone_name, zone_type, risk_level, description, geometry)
        SELECT zone_id, 1, created_at, zone_name, zone_type, risk_level, description, geometry FROM zones;
        INSERT INTO eca_rule_versions
          (rule_id, version_no, valid_from, rule_name, event_type, condition, action, severity, enabled)
        SELECT rule_id, 1, created_at, rule_name, event_type, condition, action, severity, enabled FROM eca_rules;
    """)

    op.execute("""
        CREATE FUNCTION version_zone() RETURNS trigger LANGUAGE plpgsql AS $$
        DECLARE changed timestamptz := clock_timestamp();
        BEGIN
          IF TG_OP = 'UPDATE' THEN
            IF ROW(NEW.zone_name, NEW.zone_type, NEW.risk_level, NEW.description)
               IS NOT DISTINCT FROM ROW(OLD.zone_name, OLD.zone_type, OLD.risk_level, OLD.description)
               AND ST_Equals(NEW.geometry, OLD.geometry) THEN
              RETURN NEW;
            END IF;
            NEW.version_no := OLD.version_no + 1;
            NEW.updated_at := changed;
          END IF;
          RETURN NEW;
        END $$;
        CREATE TRIGGER zone_version_before BEFORE UPDATE ON zones
        FOR EACH ROW EXECUTE FUNCTION version_zone();

        CREATE FUNCTION record_zone_version() RETURNS trigger LANGUAGE plpgsql AS $$
        DECLARE changed timestamptz := clock_timestamp();
        BEGIN
          IF TG_OP = 'UPDATE' THEN
            IF NEW.version_no = OLD.version_no THEN RETURN NEW; END IF;
            UPDATE zone_versions SET valid_to = changed WHERE zone_id = OLD.zone_id AND valid_to IS NULL;
          ELSIF TG_OP = 'DELETE' THEN
            UPDATE zone_versions SET valid_to = changed WHERE zone_id = OLD.zone_id AND valid_to IS NULL;
            RETURN OLD;
          END IF;
          INSERT INTO zone_versions
            (zone_id, version_no, valid_from, zone_name, zone_type, risk_level, description, geometry)
          VALUES (NEW.zone_id, NEW.version_no, changed, NEW.zone_name, NEW.zone_type,
                  NEW.risk_level, NEW.description, NEW.geometry);
          RETURN NEW;
        END $$;
        CREATE TRIGGER zone_version_after AFTER INSERT OR UPDATE OR DELETE ON zones
        FOR EACH ROW EXECUTE FUNCTION record_zone_version();
    """)

    op.execute("""
        CREATE FUNCTION version_rule() RETURNS trigger LANGUAGE plpgsql AS $$
        BEGIN
          IF ROW(NEW.rule_name, NEW.event_type, NEW.condition, NEW.action, NEW.severity, NEW.enabled)
             IS NOT DISTINCT FROM ROW(OLD.rule_name, OLD.event_type, OLD.condition, OLD.action, OLD.severity, OLD.enabled) THEN
            RETURN NEW;
          END IF;
          NEW.version_no := OLD.version_no + 1;
          NEW.updated_at := clock_timestamp();
          RETURN NEW;
        END $$;
        CREATE TRIGGER rule_version_before BEFORE UPDATE ON eca_rules
        FOR EACH ROW EXECUTE FUNCTION version_rule();

        CREATE FUNCTION record_rule_version() RETURNS trigger LANGUAGE plpgsql AS $$
        DECLARE changed timestamptz := clock_timestamp();
        BEGIN
          IF TG_OP = 'UPDATE' THEN
            IF NEW.version_no = OLD.version_no THEN RETURN NEW; END IF;
            UPDATE eca_rule_versions SET valid_to = changed WHERE rule_id = OLD.rule_id AND valid_to IS NULL;
          ELSIF TG_OP = 'DELETE' THEN
            UPDATE eca_rule_versions SET valid_to = changed WHERE rule_id = OLD.rule_id AND valid_to IS NULL;
            RETURN OLD;
          END IF;
          INSERT INTO eca_rule_versions
            (rule_id, version_no, valid_from, rule_name, event_type, condition, action, severity, enabled)
          VALUES (NEW.rule_id, NEW.version_no, changed, NEW.rule_name, NEW.event_type,
                  NEW.condition, NEW.action, NEW.severity, NEW.enabled);
          RETURN NEW;
        END $$;
        CREATE TRIGGER rule_version_after AFTER INSERT OR UPDATE OR DELETE ON eca_rules
        FOR EACH ROW EXECUTE FUNCTION record_rule_version();
    """)

    op.execute("""
        CREATE FUNCTION audit_configuration() RETURNS trigger LANGUAGE plpgsql AS $$
        DECLARE before_record jsonb; after_record jsonb; item_id text;
        BEGIN
          IF TG_OP <> 'INSERT' THEN before_record := to_jsonb(OLD) - 'geometry' - 'location'; END IF;
          IF TG_OP <> 'DELETE' THEN after_record := to_jsonb(NEW) - 'geometry' - 'location'; END IF;
          item_id := CASE TG_TABLE_NAME
            WHEN 'zones' THEN coalesce(after_record->>'zone_id', before_record->>'zone_id')
            WHEN 'eca_rules' THEN coalesce(after_record->>'rule_id', before_record->>'rule_id')
            WHEN 'map_pins' THEN coalesce(after_record->>'pin_id', before_record->>'pin_id')
            ELSE coalesce(after_record->>'preference_id', before_record->>'preference_id') END;
          INSERT INTO configuration_audit(entity_type, entity_id, operation, before_data, after_data)
          VALUES (TG_TABLE_NAME, item_id, TG_OP, before_record, after_record);
          RETURN NULL;
        END $$;
        CREATE TRIGGER audit_zones AFTER INSERT OR UPDATE OR DELETE ON zones
          FOR EACH ROW EXECUTE FUNCTION audit_configuration();
        CREATE TRIGGER audit_rules AFTER INSERT OR UPDATE OR DELETE ON eca_rules
          FOR EACH ROW EXECUTE FUNCTION audit_configuration();
        CREATE TRIGGER audit_pins AFTER INSERT OR UPDATE OR DELETE ON map_pins
          FOR EACH ROW EXECUTE FUNCTION audit_configuration();
        CREATE TRIGGER audit_preferences AFTER INSERT OR UPDATE OR DELETE ON map_preferences
          FOR EACH ROW EXECUTE FUNCTION audit_configuration();
    """)

    op.execute("""
        CREATE VIEW operational_hourly_summary AS
        SELECT bucket_start,
               sum(observation_count)::bigint AS observation_count,
               sum(alert_count)::bigint AS alert_count,
               sum(critical_alert_count)::bigint AS critical_alert_count
        FROM (
          SELECT date_trunc('hour', observed_at AT TIME ZONE 'UTC') AT TIME ZONE 'UTC' AS bucket_start,
                 count(*) AS observation_count, 0::bigint AS alert_count, 0::bigint AS critical_alert_count
          FROM observations GROUP BY 1
          UNION ALL
          SELECT date_trunc('hour', created_at AT TIME ZONE 'UTC') AT TIME ZONE 'UTC' AS bucket_start,
                 0::bigint, count(*), count(*) FILTER (WHERE severity = 'critical')
          FROM alerts GROUP BY 1
        ) input GROUP BY bucket_start;
    """)


def downgrade():
    op.execute("DROP VIEW operational_hourly_summary")
    for table, name in (("zones", "audit_zones"), ("eca_rules", "audit_rules"),
                        ("map_pins", "audit_pins"), ("map_preferences", "audit_preferences")):
        op.execute(f"DROP TRIGGER {name} ON {table}")
    op.execute("DROP FUNCTION audit_configuration()")
    op.execute("DROP TRIGGER rule_version_after ON eca_rules")
    op.execute("DROP TRIGGER rule_version_before ON eca_rules")
    op.execute("DROP FUNCTION record_rule_version()")
    op.execute("DROP FUNCTION version_rule()")
    op.execute("DROP TRIGGER zone_version_after ON zones")
    op.execute("DROP TRIGGER zone_version_before ON zones")
    op.execute("DROP FUNCTION record_zone_version()")
    op.execute("DROP FUNCTION version_zone()")
    op.drop_table("event_outbox")
    op.drop_table("configuration_audit")
    op.drop_table("eca_rule_versions")
    op.drop_table("zone_versions")
    op.drop_column("alerts", "rule_version")
    op.drop_column("eca_rules", "version_no")
    op.drop_column("zones", "version_no")
