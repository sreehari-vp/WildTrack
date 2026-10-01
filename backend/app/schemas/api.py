from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class DeviceOut(BaseModel):
    device_id: str
    device_code: str
    device_type: str
    status: str
    battery_level: int
    last_seen: datetime | None = None


class ZoneSummary(BaseModel):
    zone_id: str
    name: str
    zone_type: str
    risk_level: str


class AlertOut(BaseModel):
    alert_id: str
    animal_id: str
    zone_id: str | None = None
    rule_id: str | None = None
    alert_type: str
    severity: str
    message: str
    status: str
    created_at: datetime
    updated_at: datetime
    resolved_at: datetime | None = None
    animal_code: str | None = None
    animal_name: str | None = None
    species: str | None = None
    zone_name: str | None = None
    zone_type: str | None = None
    rule_name: str | None = None


class AlertStatusUpdate(BaseModel):
    status: str


class ObservationOut(BaseModel):
    observation_id: str
    animal_id: str
    device_id: str
    latitude: float
    longitude: float
    speed: float
    observed_at: datetime


class AnimalOut(BaseModel):
    animal_id: str
    animal_code: str
    species: str
    name: str
    age: int | None
    sex: str | None
    status: str
    device: DeviceOut | None = None
    latest_observation: ObservationOut | None = None
    current_zone: ZoneSummary | None = None


class MovementPoint(BaseModel):
    observation_id: str | None = None
    latitude: float
    longitude: float
    timestamp: datetime
    speed: float | None = None
    zone: ZoneSummary | None = None
    distance_from_previous_meters: float = 0


class MovementOut(BaseModel):
    animal_id: str
    points: list[MovementPoint]
    total_distance_meters: float = 0
    movement_duration_seconds: float = 0
    started_at: datetime | None = None
    ended_at: datetime | None = None
    point_count: int = 0


class ZoneTransition(BaseModel):
    from_zone: ZoneSummary | None = None
    to_zone: ZoneSummary | None = None
    transitioned_at: datetime
    entered_at: datetime | None = None
    exited_at: datetime | None = None
    duration_seconds: float | None = None


class ZoneHistorySegment(BaseModel):
    zone: ZoneSummary | None = None
    entered_at: datetime
    exited_at: datetime | None = None
    duration_seconds: float = 0


class ZoneHistoryOut(BaseModel):
    animal_id: str
    segments: list[ZoneHistorySegment]
    transitions: list[ZoneTransition]


class TimelineEvent(BaseModel):
    event_type: str
    timestamp: datetime
    latitude: float | None = None
    longitude: float | None = None
    zone: ZoneSummary | None = None
    from_zone: ZoneSummary | None = None
    to_zone: ZoneSummary | None = None
    distance_from_previous_meters: float | None = None


class TimelineOut(BaseModel):
    animal_id: str
    events: list[TimelineEvent]


class DistanceOut(BaseModel):
    animal_id: str
    total_distance_meters: float
    started_at: datetime | None = None
    ended_at: datetime | None = None
    point_count: int


class NearbyZoneOut(BaseModel):
    zone_id: str
    zone_name: str
    zone_type: str
    risk_level: str
    distance_meters: float


class NearbyAnimalOut(BaseModel):
    animal_id: str
    animal_code: str
    species: str
    name: str
    latitude: float
    longitude: float
    observed_at: datetime
    distance_meters: float


class ZoneOut(BaseModel):
    zone_id: str
    zone_name: str
    zone_type: str
    risk_level: str
    description: str | None
    geometry: dict[str, Any]


class SimulationAnimalStatus(BaseModel):
    current_step: int
    current_zone: str | None = None


class SimulationStatus(BaseModel):
    running: bool
    interval_seconds: float
    animals: dict[str, SimulationAnimalStatus] = Field(default_factory=dict)
    task_active: bool = False
