from dataclasses import dataclass


@dataclass(frozen=True)
class SimulationPoint:
    longitude: float
    latitude: float


SIMULATION_PATHS: dict[str, list[SimulationPoint]] = {
    # Safe -> Buffer -> Restricted -> Buffer. This is the Phase 3 demonstration path.
    "EL-001": [
        SimulationPoint(76.6440, 11.4510),
        SimulationPoint(76.6620, 11.4460),
        SimulationPoint(76.6810, 11.4410),
        SimulationPoint(76.7040, 11.4380),
        SimulationPoint(76.6630, 11.4210),
        SimulationPoint(76.6510, 11.4140),
        SimulationPoint(76.6550, 11.4170),
    ],
    # Protected -> High-risk -> Protected.
    "TG-001": [
        SimulationPoint(76.6850, 11.3810),
        SimulationPoint(76.6960, 11.3860),
        SimulationPoint(76.7120, 11.3920),
        SimulationPoint(76.7220, 11.4050),
        SimulationPoint(76.7040, 11.3910),
    ],
    # Safe -> Water source -> Safe edge.
    "DR-001": [
        SimulationPoint(76.6330, 11.4440),
        SimulationPoint(76.6280, 11.4315),
        SimulationPoint(76.6240, 11.4140),
        SimulationPoint(76.6300, 11.3940),
        SimulationPoint(76.6420, 11.3840),
        SimulationPoint(76.6120, 11.3860),
    ],
}

SPECIES_SPEED_CAP_KMH = {
    "elephant": 18.0,
    "tiger": 28.0,
    "deer": 32.0,
}
