from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field, field_validator


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
    rule_version: int | None = None
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
    area_km2: float = 0
    zone_id: str
    zone_name: str
    zone_type: str
    risk_level: str
    description: str | None
    geometry: dict[str, Any]
    created_in_app: bool = False
    version_no: int = 1


class ZoneWrite(BaseModel):
    zone_name: str = Field(min_length=1, max_length=120)
    zone_type: str
    risk_level: str
    description: str = Field(default="", max_length=2000)
    geometry: dict[str, Any]

    @field_validator("zone_name")
    @classmethod
    def valid_name(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("Zone name is required")
        return value.strip()

    @field_validator("zone_type")
    @classmethod
    def valid_type(cls, value: str) -> str:
        if value not in {"safe", "buffer", "restricted", "high-risk", "water-source", "protected"}:
            raise ValueError("Unknown zone type")
        return value

    @field_validator("risk_level")
    @classmethod
    def valid_risk(cls, value: str) -> str:
        if value not in {"safe", "info", "low", "medium", "high", "critical"}:
            raise ValueError("Unknown risk level")
        return value

    @field_validator("geometry")
    @classmethod
    def valid_geometry_shape(cls, value: dict[str, Any]) -> dict[str, Any]:
        if value.get("type") not in {"Polygon", "MultiPolygon"} or not isinstance(value.get("coordinates"), list):
            raise ValueError("A polygon or multipolygon is required")
        return value


class PinWrite(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    type: str
    coordinates: tuple[float, float]

    @field_validator("name")
    @classmethod
    def valid_name(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("Pin name is required")
        return value.strip()

    @field_validator("type")
    @classmethod
    def valid_type(cls, value: str) -> str:
        if value not in {"Observation", "Patrol", "Camera", "Hazard"}:
            raise ValueError("Unknown pin type")
        return value

    @field_validator("coordinates")
    @classmethod
    def valid_coordinates(cls, value: tuple[float, float]) -> tuple[float, float]:
        if not (-180 <= value[0] <= 180 and -90 <= value[1] <= 90):
            raise ValueError("Invalid longitude or latitude")
        return value


class PinOut(PinWrite):
    id: str
    created_at: datetime


class MapPreferences(BaseModel):
    layer_mode: str = "plain"
    boundary_visible: bool = True
    zones_visible: bool = True
    animals_visible: bool = True
    paths_visible: bool = True
    pins_visible: bool = True
    labels_visible: bool = False

    @field_validator("layer_mode")
    @classmethod
    def valid_layer(cls, value: str) -> str:
        if value not in {"plain", "terrain", "satellite"}:
            raise ValueError("Unknown map layer")
        return value


class RuleWrite(BaseModel):
    rule_name: str = Field(min_length=1, max_length=120)
    event_type: str = Field(min_length=1, max_length=60)
    condition: dict[str, Any]
    action: dict[str, Any]
    severity: str
    enabled: bool = True

    @field_validator("rule_name")
    @classmethod
    def valid_rule_name(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Rule name cannot be blank")
        return value

    @field_validator("event_type")
    @classmethod
    def valid_event_type(cls, value: str) -> str:
        if value not in {"zone_entry", "zone_exit", "restricted_zone_entry", "protected_zone_entry", "high_risk_zone_entry", "low_battery"}:
            raise ValueError("Unknown rule event type")
        return value

    @field_validator("condition")
    @classmethod
    def valid_condition(cls, value: dict[str, Any]) -> dict[str, Any]:
        supported = {"zone_type", "risk_level", "species", "battery_level_lt", "distance_to_boundary_lt", "time_in_zone_gt", "distance_travelled_gt"}
        if not set(value).issubset(supported):
            raise ValueError("Unknown rule condition")
        for key in supported & set(value):
            if key.endswith(("_lt", "_gt")):
                try:
                    float(value[key])
                except (TypeError, ValueError):
                    raise ValueError(f"{key} must be numeric") from None
        return value

    @field_validator("action")
    @classmethod
    def valid_action(cls, value: dict[str, Any]) -> dict[str, Any]:
        if set(value) != {"create_alert"} or not isinstance(value["create_alert"], bool):
            raise ValueError("Only a create_alert boolean action is supported")
        return value

    @field_validator("severity")
    @classmethod
    def valid_severity(cls, value: str) -> str:
        if value not in {"info", "low", "medium", "high", "critical"}:
            raise ValueError("Unknown severity")
        return value


class RuleOut(RuleWrite):
    rule_id: str
    version_no: int


class SimulationAnimalStatus(BaseModel):
    current_step: int
    current_zone: str | None = None


class SimulationStatus(BaseModel):
    running: bool
    interval_seconds: float
    animals: dict[str, SimulationAnimalStatus] = Field(default_factory=dict)
    task_active: bool = False
    finished: bool = False
    completed_routes: int = 0
    total_routes: int = 0
