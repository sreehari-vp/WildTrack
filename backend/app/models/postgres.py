from datetime import datetime
from typing import Any

from geoalchemy2 import Geometry
from sqlalchemy import Boolean, CheckConstraint, DateTime, ForeignKey, Index, Integer, Numeric, String, Text, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)


class Device(TimestampMixin, Base):
    __tablename__ = "devices"

    device_id: Mapped[str] = mapped_column(String(32), primary_key=True)
    device_code: Mapped[str] = mapped_column(String(32), nullable=False, unique=True)
    device_type: Mapped[str] = mapped_column(String(40), nullable=False)
    status: Mapped[str] = mapped_column(String(24), nullable=False)
    battery_level: Mapped[int] = mapped_column(Integer, nullable=False)
    last_seen: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    animal: Mapped["Animal"] = relationship(back_populates="device", uselist=False)


class Animal(TimestampMixin, Base):
    __tablename__ = "animals"
    __table_args__ = (
        UniqueConstraint("animal_code", name="uq_animals_animal_code"),
        Index("ix_animals_species", "species"),
        Index("ix_animals_status", "status"),
    )

    animal_id: Mapped[str] = mapped_column(String(32), primary_key=True)
    animal_code: Mapped[str] = mapped_column(String(32), nullable=False)
    species: Mapped[str] = mapped_column(String(32), nullable=False)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    age: Mapped[int | None] = mapped_column(Integer)
    sex: Mapped[str | None] = mapped_column(String(16))
    status: Mapped[str] = mapped_column(String(24), nullable=False)
    device_id: Mapped[str | None] = mapped_column(ForeignKey("devices.device_id", ondelete="SET NULL"), unique=True)

    device: Mapped[Device | None] = relationship(back_populates="animal")
    observations: Mapped[list["Observation"]] = relationship(back_populates="animal")
    alerts: Mapped[list["Alert"]] = relationship(back_populates="animal")


class ForestBoundary(TimestampMixin, Base):
    __tablename__ = "forest_boundaries"

    boundary_id: Mapped[str] = mapped_column(String(32), primary_key=True)
    boundary_name: Mapped[str] = mapped_column(String(120), nullable=False, unique=True)
    description: Mapped[str | None] = mapped_column(Text)
    geometry: Mapped[Any] = mapped_column(Geometry("MULTIPOLYGON", srid=4326), nullable=False)


class Zone(TimestampMixin, Base):
    __tablename__ = "zones"
    __table_args__ = (
        Index("ix_zones_zone_type", "zone_type"),
        Index("ix_zones_risk_level", "risk_level"),
    )

    zone_id: Mapped[str] = mapped_column(String(32), primary_key=True)
    zone_name: Mapped[str] = mapped_column(String(120), nullable=False, unique=True)
    zone_type: Mapped[str] = mapped_column(String(32), nullable=False)
    risk_level: Mapped[str] = mapped_column(String(24), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    created_in_app: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    version_no: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    geometry: Mapped[Any] = mapped_column(Geometry("MULTIPOLYGON", srid=4326), nullable=False)

    alerts: Mapped[list["Alert"]] = relationship(back_populates="zone")


class Observation(Base):
    __tablename__ = "observations"
    __table_args__ = (
        CheckConstraint("latitude BETWEEN -90 AND 90", name="ck_observations_latitude"),
        CheckConstraint("longitude BETWEEN -180 AND 180", name="ck_observations_longitude"),
        Index("ix_observations_animal_observed_at", "animal_id", "observed_at"),
        Index("ix_observations_device_observed_at", "device_id", "observed_at"),
    )

    observation_id: Mapped[str] = mapped_column(String(32), primary_key=True)
    animal_id: Mapped[str] = mapped_column(ForeignKey("animals.animal_id", ondelete="CASCADE"), nullable=False)
    device_id: Mapped[str] = mapped_column(ForeignKey("devices.device_id", ondelete="CASCADE"), nullable=False)
    latitude: Mapped[float] = mapped_column(Numeric(9, 6), nullable=False)
    longitude: Mapped[float] = mapped_column(Numeric(9, 6), nullable=False)
    location: Mapped[Any] = mapped_column(Geometry("POINT", srid=4326), nullable=False)
    speed: Mapped[float] = mapped_column(Numeric(6, 2), nullable=False)
    observed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    animal: Mapped[Animal] = relationship(back_populates="observations")


class EcaRule(TimestampMixin, Base):
    __tablename__ = "eca_rules"
    __table_args__ = (Index("ix_eca_rules_event_type", "event_type"), Index("ix_eca_rules_enabled", "enabled"))

    rule_id: Mapped[str] = mapped_column(String(32), primary_key=True)
    rule_name: Mapped[str] = mapped_column(String(120), nullable=False, unique=True)
    event_type: Mapped[str] = mapped_column(String(60), nullable=False)
    condition: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    action: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    severity: Mapped[str] = mapped_column(String(24), nullable=False)
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    version_no: Mapped[int] = mapped_column(Integer, nullable=False, default=1)

    alerts: Mapped[list["Alert"]] = relationship(back_populates="rule")


class Alert(TimestampMixin, Base):
    __tablename__ = "alerts"
    __table_args__ = (
        Index("ix_alerts_status_severity", "status", "severity"),
        Index("ix_alerts_created_at", "created_at"),
    )

    alert_id: Mapped[str] = mapped_column(String(32), primary_key=True)
    animal_id: Mapped[str] = mapped_column(ForeignKey("animals.animal_id", ondelete="CASCADE"), nullable=False)
    zone_id: Mapped[str | None] = mapped_column(ForeignKey("zones.zone_id", ondelete="SET NULL"))
    rule_id: Mapped[str | None] = mapped_column(ForeignKey("eca_rules.rule_id", ondelete="SET NULL"))
    rule_version: Mapped[int | None] = mapped_column(Integer)
    alert_type: Mapped[str] = mapped_column(String(60), nullable=False)
    severity: Mapped[str] = mapped_column(String(24), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(24), nullable=False)
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    animal: Mapped[Animal] = relationship(back_populates="alerts")
    zone: Mapped[Zone | None] = relationship(back_populates="alerts")
    rule: Mapped[EcaRule | None] = relationship(back_populates="alerts")
