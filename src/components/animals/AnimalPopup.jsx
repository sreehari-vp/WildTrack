import { Navigation, Route, Waypoints } from "lucide-react";
import { useNavigate } from "react-router-dom";
import { directionLabel, formatCoordinate, formatRelative, titleCase } from "../../utils/format";
import { Button } from "../common/Button";
import { RiskBadge, StatusBadge } from "./StatusBadge";
import { SpeciesIcon } from "./SpeciesIcon";
const AnimalPopup = ({
  animal,
  zone,
  device,
  movementSummary,
  onViewOnMap
}) => {
  const navigate = useNavigate();
  const distanceKm = movementSummary?.total_distance_meters ? (movementSummary.total_distance_meters / 1e3).toFixed(2) : null;
  return <div className="w-72 rounded-panel border border-line bg-paper p-3 shadow-md">
      <div className="flex items-start gap-3">
        <div className="grid h-10 w-10 place-items-center rounded-control bg-moss-100 text-forest-950">
          <SpeciesIcon species={animal.species} />
        </div>
        <div className="min-w-0">
          <div className="font-mono text-sm font-medium tabular">{animal.id}</div>
          <div className="truncate text-sm text-ink-600">{animal.name}</div>
          <div className="text-xs text-ink-400">{titleCase(animal.species)}</div>
        </div>
      </div>
      <div className="mt-3 flex flex-wrap gap-2">
        <StatusBadge status={animal.status} />
        <RiskBadge risk={animal.risk} />
      </div>
      <dl className="mt-3 grid grid-cols-2 gap-x-4 gap-y-2 text-sm">
        <div>
          <dt className="text-xs text-ink-400">Zone</dt>
          <dd className="truncate text-ink-900">{zone?.name ?? "Outside reserve"}</dd>
        </div>
        <div>
          <dt className="text-xs text-ink-400">Speed</dt>
          <dd className="tabular">{animal.speedKmh.toFixed(1)} km/h</dd>
        </div>
        <div>
          <dt className="text-xs text-ink-400">Direction</dt>
          <dd>{directionLabel(animal.direction)}</dd>
        </div>
        <div>
          <dt className="text-xs text-ink-400">Battery</dt>
          <dd className="tabular">{device?.battery ?? "--"}%</dd>
        </div>
        <div className="col-span-2">
          <dt className="text-xs text-ink-400">Last seen</dt>
          <dd>{formatRelative(animal.lastSeen)}</dd>
        </div>
        <div className="col-span-2">
          <dt className="text-xs text-ink-400">Distance travelled</dt>
          <dd className="font-mono text-xs tabular">{distanceKm ? `${distanceKm} km` : "No route history"}</dd>
        </div>
        <div className="col-span-2">
          <dt className="text-xs text-ink-400">Coordinates</dt>
          <dd className="font-mono text-xs tabular">
            {formatCoordinate(animal.coordinates[1])}, {formatCoordinate(animal.coordinates[0])}
          </dd>
        </div>
      </dl>
      <div className="mt-4 grid grid-cols-3 gap-2">
        <Button className="px-2" icon={<Route className="h-4 w-4" strokeWidth={1.75} />} onClick={() => navigate(`/animals/${animal.id}`)}>
          View animal
        </Button>
        <Button className="px-2" icon={<Waypoints className="h-4 w-4" strokeWidth={1.75} />} onClick={() => navigate(`/movement-history?animal=${animal.id}`)}>
          Movement
        </Button>
        <Button className="px-2" variant="primary" icon={<Navigation className="h-4 w-4" strokeWidth={1.75} />} onClick={onViewOnMap}>
          View on map
        </Button>
      </div>
    </div>;
};
export {
  AnimalPopup
};
