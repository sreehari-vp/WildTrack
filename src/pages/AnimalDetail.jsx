import { useNavigate, useParams } from "react-router-dom";
import { ForestMap } from "../components/map/ForestMap";
import { RiskBadge, StatusBadge } from "../components/animals/StatusBadge";
import { SpeciesIcon } from "../components/animals/SpeciesIcon";
import { AlertList } from "../components/alerts/AlertList";
import { useAnimal, useAnimals } from "../hooks/useAnimals";
import { useAlerts } from "../hooks/useAlerts";
import { useBoundary, useZones } from "../hooks/useZones";
import { useDevices } from "../hooks/useDevices";
import { useMovementForAnimal } from "../hooks/useObservations";
import { directionLabel, formatCoordinate, formatRelative, titleCase } from "../utils/format";
import { movementPathsFromObservations } from "../utils/movement";
import { DataState } from "./PageState";
const formatDistanceKm = (meters = 0) => `${(meters / 1e3).toFixed(2)} km`;
const formatDuration = (seconds = 0) => {
  const minutes = Math.round(seconds / 60);
  if (minutes < 60) return `${minutes} min`;
  const hours = Math.floor(minutes / 60);
  return `${hours} hr ${minutes % 60} min`;
};
const AnimalDetail = () => {
  const navigate = useNavigate();
  const { id = "" } = useParams();
  const animal = useAnimal(id);
  const animals = useAnimals();
  const zones = useZones();
  const alerts = useAlerts();
  const devices = useDevices();
  const boundary = useBoundary();
  const movement = useMovementForAnimal(id, { limit: 2000 });
  const loading = animal.loading || animals.loading || zones.loading || alerts.loading || devices.loading || boundary.loading || movement.loading;
  const error = animal.error || animals.error || zones.error || alerts.error || devices.error || boundary.error || movement.error;
  if (loading || error || !animal.data || !animals.data || !zones.data || !alerts.data || !devices.data || !boundary.data || !movement.data) {
    return <div className="p-6"><DataState loading={loading} error={error} empty={!loading && !animal.data} onRetry={() => window.location.reload()} /></div>;
  }
  const currentAnimal = animal.data;
  const device = devices.data.find((item) => item.id === currentAnimal.deviceId);
  const zone = zones.data.find((item) => item.id === currentAnimal.currentZoneId);
  const relatedAlerts = alerts.data.filter((alert) => alert.animalId === currentAnimal.id);
  const movementObservations = movement.data.observations ?? [];
  return <div className="space-y-6 p-6">
      <header className="flex flex-wrap items-center justify-between gap-4 border-b border-line pb-5">
        <div className="flex items-center gap-4">
          <div className="grid h-14 w-14 place-items-center rounded-panel bg-moss-100 text-forest-950"><SpeciesIcon species={currentAnimal.species} className="h-8 w-8" /></div>
          <div><p className="font-mono text-sm tabular text-ink-600">{currentAnimal.id}</p><h2 className="font-display text-3xl">{currentAnimal.name}</h2></div>
        </div>
        <div className="flex gap-2"><StatusBadge status={currentAnimal.status} /><RiskBadge risk={currentAnimal.risk} /></div>
      </header>
      <div className="grid gap-6 xl:grid-cols-[0.9fr_1.1fr]">
        <section className="surface p-5">
          <h3 className="mb-4 font-medium">Key facts</h3>
          <dl className="grid grid-cols-2 gap-x-8 gap-y-4 text-sm">
            <div><dt className="text-xs text-ink-400">Species</dt><dd>{titleCase(currentAnimal.species)}</dd></div>
            <div><dt className="text-xs text-ink-400">Current zone</dt><dd>{zone?.name}</dd></div>
            <div><dt className="text-xs text-ink-400">Coordinates</dt><dd className="font-mono tabular">{formatCoordinate(currentAnimal.coordinates[1])}, {formatCoordinate(currentAnimal.coordinates[0])}</dd></div>
            <div><dt className="text-xs text-ink-400">Speed</dt><dd>{currentAnimal.speedKmh.toFixed(1)} km/h</dd></div>
            <div><dt className="text-xs text-ink-400">Direction</dt><dd>{directionLabel(currentAnimal.direction)}</dd></div>
            <div><dt className="text-xs text-ink-400">Battery</dt><dd>{device?.battery}%</dd></div>
            <div><dt className="text-xs text-ink-400">Last seen</dt><dd>{formatRelative(currentAnimal.lastSeen)}</dd></div>
            <div><dt className="text-xs text-ink-400">Device</dt><dd>{device?.model} · {device?.id}</dd></div>
          </dl>
        </section>
        <section className="overflow-hidden rounded-panel border border-line"><ForestMap animals={[currentAnimal]} devices={devices.data} zones={zones.data} boundary={boundary.data} movementPaths={movementPathsFromObservations(movementObservations)} selectedAnimalId={currentAnimal.id} preview className="h-[360px]" /></section>
      </div>
      <div className="grid gap-6 xl:grid-cols-[1fr_0.8fr]">
        <section><h3 className="mb-3 font-medium">Recent alerts</h3><AlertList alerts={relatedAlerts} animals={animals.data} zones={zones.data} onSelect={(alert) => navigate(`/alerts/${alert.id}`)} /></section>
        <section className="divider-row grid grid-cols-2 rounded-panel border border-line bg-paper">
          {[["Distance travelled", formatDistanceKm(movement.data.total_distance_meters)], ["Time active", formatDuration(movement.data.movement_duration_seconds)], ["Zones visited", new Set(movementObservations.map((item) => item.zoneId).filter(Boolean)).size], ["Alerts generated", relatedAlerts.length]].map(([label, value]) => <div key={label} className="p-4"><div className="font-display text-3xl tabular">{value}</div><div className="text-xs text-ink-600">{label}</div></div>)}
        </section>
      </div>
    </div>;
};
export {
  AnimalDetail
};
