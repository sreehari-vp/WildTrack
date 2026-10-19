"""Add transparent scenario attention levels to Ooty's land-cover zones."""

from alembic import op

revision = "0010_ooty_zone_attention"
down_revision = "0009_ooty_canonical_dataset"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # These are demonstration/monitoring categories inferred from land cover,
    # not a sourced or official hazard assessment.
    op.execute("""
        UPDATE zones
        SET risk_level = CASE zone_type
                WHEN 'tree_cover' THEN 'safe'
                WHEN 'grassland' THEN 'low'
                WHEN 'bare_or_sparse_cover' THEN 'low'
                WHEN 'cultivated_land' THEN 'medium'
                WHEN 'surface_water' THEN 'medium'
                WHEN 'built_up' THEN 'high'
                ELSE 'info'
            END,
            description = concat_ws(' ', nullif(description, ''),
                'Scenario monitoring category inferred from land cover; not an official hazard assessment.')
        WHERE zone_id LIKE 'OTY-%'
    """)
    op.execute("""
        INSERT INTO eca_rules
            (rule_id, rule_name, event_type, condition, action, severity, enabled)
        VALUES
            ('RULE-OTY-DANGER', 'Ooty danger-class zone entry', 'zone_entry',
             jsonb_build_object('risk_level', 'high'), jsonb_build_object('create_alert', true), 'high', true),
            ('RULE-OTY-LOW-BATTERY', 'Ooty tracker low battery', 'low_battery',
             jsonb_build_object('battery_level_lt', 20), jsonb_build_object('create_alert', true), 'medium', true)
        ON CONFLICT (rule_id) DO NOTHING
    """)


def downgrade() -> None:
    op.execute("DELETE FROM eca_rules WHERE rule_id IN ('RULE-OTY-DANGER', 'RULE-OTY-LOW-BATTERY')")
    op.execute("""
        UPDATE zones
        SET risk_level='info',
            description=replace(description,
                ' Scenario monitoring category inferred from land cover; not an official hazard assessment.', '')
        WHERE zone_id LIKE 'OTY-%'
    """)
