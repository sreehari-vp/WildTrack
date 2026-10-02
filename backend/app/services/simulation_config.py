from dataclasses import dataclass
from math import ceil, cos, radians, sqrt


@dataclass(frozen=True)
class SimulationPoint:
    longitude: float
    latitude: float


def _route(
    *coordinates: tuple[float, float],
    max_step_m: float = 600,
) -> list[SimulationPoint]:
    """Expand route landmarks into GPS fixes with a controlled maximum step."""
    if len(coordinates) < 3:
        raise ValueError("A route needs at least three waypoints")
    points = [SimulationPoint(*coordinates[0])]
    for start, end in zip(coordinates, coordinates[1:]):
        mean_latitude = radians((start[1] + end[1]) / 2)
        east_m = (end[0] - start[0]) * 111_320 * cos(mean_latitude)
        north_m = (end[1] - start[1]) * 110_540
        segments = max(1, ceil(sqrt(east_m ** 2 + north_m ** 2) / max_step_m))
        for index in range(1, segments + 1):
            fraction = index / segments
            points.append(SimulationPoint(
                round(start[0] + (end[0] - start[0]) * fraction, 6),
                round(start[1] + (end[1] - start[1]) * fraction, 6),
            ))
    return points


# Crossing routes use several landmarks on each side of a shared zone boundary.
# The three pairs form Safe <-> Buffer <-> High-risk <-> Protected.
SIMULATION_PATHS: dict[str, list[SimulationPoint]] = {
    "EL-001": _route(
        (76.644, 11.451), (76.653, 11.449), (76.661, 11.447), (76.668, 11.445),
        (76.675, 11.444), (76.682, 11.444), (76.690, 11.446), (76.696, 11.448),
        (76.702, 11.451), (76.708, 11.455), (76.714, 11.457),
        max_step_m=1200,
    ),
    "EL-003": _route(
        (76.651, 11.457), (76.658, 11.453), (76.665, 11.448), (76.669, 11.443),
        (76.676, 11.443), (76.683, 11.444), (76.690, 11.448), (76.696, 11.450),
        (76.703, 11.453), (76.710, 11.454), (76.716, 11.456),
        max_step_m=1200,
    ),
    "DR-005": _route(
        (76.684, 11.449), (76.690, 11.444), (76.699, 11.438), (76.702, 11.434),
        (76.703, 11.427), (76.702, 11.419), (76.699, 11.412), (76.697, 11.405),
        (76.695, 11.399), (76.691, 11.394), (76.686, 11.391),
        max_step_m=1200,
    ),
    "TG-001": _route(
        (76.703, 11.419), (76.702, 11.411), (76.700, 11.404), (76.699, 11.399),
        (76.698, 11.394), (76.696, 11.387), (76.690, 11.382), (76.683, 11.379),
        (76.677, 11.376), (76.671, 11.374), (76.665, 11.373),
        max_step_m=1200,
    ),
    "TG-005": _route(
        (76.714, 11.418), (76.709, 11.410), (76.707, 11.403), (76.705, 11.399),
        (76.704, 11.393), (76.701, 11.386), (76.696, 11.380), (76.691, 11.376),
        (76.685, 11.374), (76.679, 11.373), (76.673, 11.372),
        max_step_m=1200,
    ),
    # Resident animals continue through their habitat without snapping home.
    "EL-004": _route((76.681, 11.441), (76.686, 11.443), (76.691, 11.445), (76.696, 11.447), (76.701, 11.449), (76.706, 11.451)),
    "EL-005": _route((76.651, 11.414), (76.653, 11.416), (76.655, 11.417), (76.658, 11.419), (76.662, 11.421), (76.666, 11.422)),
    "EL-006": _route((76.699, 11.414), (76.702, 11.417), (76.705, 11.420), (76.707, 11.423), (76.710, 11.426), (76.713, 11.429)),
    "TG-003": _route((76.696, 11.384), (76.693, 11.382), (76.690, 11.380), (76.687, 11.378), (76.683, 11.376), (76.679, 11.375)),
    "TG-004": _route((76.699, 11.414), (76.702, 11.411), (76.705, 11.408), (76.708, 11.405), (76.711, 11.402), (76.714, 11.399)),
    "TG-006": _route((76.704, 11.374), (76.700, 11.376), (76.696, 11.378), (76.692, 11.380), (76.688, 11.382), (76.684, 11.384)),
    "DR-001": _route((76.640, 11.385), (76.637, 11.384), (76.634, 11.382), (76.631, 11.381), (76.628, 11.379), (76.625, 11.378)),
    "DR-004": _route((76.644, 11.451), (76.648, 11.453), (76.652, 11.455), (76.656, 11.457), (76.660, 11.459), (76.664, 11.460)),
    "DR-006": _route((76.640, 11.385), (76.639, 11.386), (76.637, 11.388), (76.635, 11.390), (76.632, 11.392), (76.629, 11.394)),
    "DR-007": _route((76.696, 11.384), (76.699, 11.386), (76.702, 11.388), (76.705, 11.390), (76.708, 11.392), (76.711, 11.394)),
}

# Continue every route through the reserve's main habitat chain.  This keeps
# local starts, then gives each tracked animal a long multi-zone exploration
# loop instead of ending after a short in-zone segment.
_EXPLORATION_LOOP = (
    (76.640, 11.385),  # water source
    (76.650, 11.415),  # restricted corridor
    (76.650, 11.450),  # north safe habitat
    (76.700, 11.450),  # buffer patrol area
    (76.700, 11.415),  # high-risk ridge
    (76.690, 11.380),  # protected habitat
    (76.640, 11.385),  # return to water source
)
for _animal_id, _path in list(SIMULATION_PATHS.items()):
    _last = _path[-1]
    _extension = _route(
        (_last.longitude, _last.latitude), *_EXPLORATION_LOOP,
        max_step_m=1200,
    )
    SIMULATION_PATHS[_animal_id] = _path + _extension[1:]


SPECIES_SPEED_CAP_KMH = {
    "elephant": 18.0,
    "tiger": 28.0,
    "deer": 32.0,
}
