import { Pause, Play, RotateCcw, Search, SkipBack, SkipForward } from "lucide-react";
import { useEffect, useMemo, useState } from "react";
import { useSearchParams } from "react-router-dom";
import { ForestMap } from "../components/map/ForestMap";
import { Button } from "../components/common/Button";
import { Select } from "../components/common/Select";
import { useAlerts } from "../hooks/useAlerts";
import { useAnimals } from "../hooks/useAnimals";
import { useBoundary, useZones } from "../hooks/useZones";
import { useDevices } from "../hooks/useDevices";
import { useMovementForAnimal, useTimelineForAnimal, useZoneHistoryForAnimal } from "../hooks/useObservations";
import { formatTime } from "../utils/format";
import { movementPathsFromObservations } from "../utils/movement";
import { DataState } from "./PageState";

const toQueryTime = (value) => value ? new Date(value).toISOString() : void 0;
const formatDistanceKm = (meters = 0) => (meters / 1e3).toFixed(2);
const formatDuration = (seconds = 0) => {
  const minutes = Math.round(seconds / 60);
  if (minutes < 60) return `${minutes} min`;
  const hours = Math.floor(minutes / 60);
  return `${hours} hr ${minutes % 60} min`;
};
const zoneLabel = (zone) => zone?.name ?? "Outside reserve";

const MovementHistory = () => {
  const [params, setParams] = useSearchParams();
  const pollingMs = Number(import.meta.env.VITE_API_POLLING_INTERVAL_MS ?? 5e3);
  const animals = useAnimals(pollingMs);
  const devices = useDevices(pollingMs);
  const zones = useZones();
  const boundary = useBoundary();
  const alerts = useAlerts();
  const selectedAnimalId = params.get("animal") ?? animals.data?.[0]?.id;
  const selectedAnimal = animals.data?.find((animal) => animal.id === selectedAnimalId) ?? animals.data?.[0];
  const [draftRange, setDraftRange] = useState({ start: "", end: "" });
  const [range, setRange] = useState({ start: "", end: "" });
  const movementParams = useMemo(
    () => ({ startTime: toQueryTime(range.start), endTime: toQueryTime(range.end), limit: 2000 }),
    [range.end, range.start]
  );
  const movement = useMovementForAnimal(selectedAnimal?.id, movementParams);
  const zoneHistory = useZoneHistoryForAnimal(selectedAnimal?.id, movementParams);
  const timeline = useTimelineForAnimal(selectedAnimal?.id, movementParams);
  const [playing, setPlaying] = useState(false);
  const [step, setStep] = useState(0);
  const animalObservations = movement.data?.observations ?? [];
  const currentPoint = animalObservations[Math.min(step, Math.max(0, animalObservations.length - 1))];
  const path = useMemo(
    () => selectedAnimal ? movementPathsFromObservations(animalObservations).filter((item) => item.animalId === selectedAnimal.id) : [],
    [animalObservations, selectedAnimal?.id]
  );
  const selectedSnapshot = selectedAnimal ? currentPoint ? [{ ...selectedAnimal, coordinates: currentPoint.coordinates, speedKmh: currentPoint.speedKmh }] : [selectedAnimal] : [];
  const rangeInvalid = Boolean(draftRange.start && draftRange.end && new Date(draftRange.start) > new Date(draftRange.end));
  const loading = animals.loading || devices.loading || zones.loading || boundary.loading || alerts.loading || movement.loading || zoneHistory.loading || timeline.loading;
  const error = animals.error || devices.error || zones.error || boundary.error || alerts.error || movement.error || zoneHistory.error || timeline.error;

  useEffect(() => {
    setStep(0);
    setPlaying(false);
  }, [selectedAnimal?.id, animalObservations.length]);

  useEffect(() => {
    if (!playing || animalObservations.length < 2) return;
    const timer = window.setInterval(() => {
      setStep((value) => {
        if (value >= animalObservations.length - 1) {
          setPlaying(false);
          return value;
        }
        return value + 1;
      });
    }, 900);
    return () => window.clearInterval(timer);
  }, [animalObservations.length, playing]);

  if (loading || error || !animals.data || !devices.data || !zones.data || !boundary.data || !alerts.data || !selectedAnimal || !movement.data || !zoneHistory.data || !timeline.data) {
    return <div className="p-6"><DataState loading={loading} error={error} onRetry={() => window.location.reload()} /></div>;
  }

  return <div className="grid h-[calc(100vh-56px)] grid-cols-[360px_minmax(0,1fr)] gap-0 max-lg:grid-cols-1 max-lg:h-auto">
      <aside className="overflow-auto border-r border-line bg-paper p-5 max-lg:border-r-0 max-lg:border-b">
        <h2 className="font-display text-2xl">Movement history</h2>
        <p className="mt-1 text-sm text-ink-600">Routes are reconstructed from ordered GPS observations and PostGIS zone detection.</p>
        <div className="mt-5 space-y-4">
          <label className="block text-xs text-ink-600">
            Animal
            <Select
    className="mt-1 w-full"
    value={selectedAnimal.id}
    onChange={(event) => {
      setParams({ animal: event.target.value });
      setStep(0);
    }}
  >
              {animals.data.map((animal) => <option key={animal.id} value={animal.id}>{animal.id} · {animal.name}</option>)}
            </Select>
          </label>
          <div className="grid grid-cols-2 gap-2">
            <label className="block text-xs text-ink-600">
              Start
              <input className="mt-1 min-h-9 w-full rounded-control border border-line bg-paper px-3 py-2 text-sm" type="datetime-local" value={draftRange.start} onChange={(event) => setDraftRange((current) => ({ ...current, start: event.target.value }))} />
            </label>
            <label className="block text-xs text-ink-600">
              End
              <input className="mt-1 min-h-9 w-full rounded-control border border-line bg-paper px-3 py-2 text-sm" type="datetime-local" value={draftRange.end} onChange={(event) => setDraftRange((current) => ({ ...current, end: event.target.value }))} />
            </label>
          </div>
          {rangeInvalid ? <div className="text-xs text-[color:var(--risk-critical)]">Start time must be before end time.</div> : null}
          <Button className="w-full" icon={<Search className="h-4 w-4" strokeWidth={1.75} />} disabled={rangeInvalid} onClick={() => setRange(draftRange)}>
            Load movement history
          </Button>
          <div className="rounded-panel border border-line p-3">
            <div className="flex items-center justify-between">
              <div>
                <div className="font-mono text-sm tabular">{selectedAnimal.id}</div>
                <div className="text-xs text-ink-600">{currentPoint ? formatTime(currentPoint.recordedAt) : "No route points"}</div>
              </div>
              <Button disabled={animalObservations.length < 2} variant={playing ? "secondary" : "primary"} icon={playing ? <Pause className="h-4 w-4" strokeWidth={1.75} /> : <Play className="h-4 w-4" strokeWidth={1.75} />} onClick={() => setPlaying((value) => !value)}>
                {playing ? "Pause" : "Play"}
              </Button>
            </div>
            <input
    className="mt-4 w-full accent-[color:var(--forest-700)]"
    type="range"
    min={0}
    max={Math.max(0, animalObservations.length - 1)}
    value={step}
    onChange={(event) => setStep(Number(event.target.value))}
  />
            <div className="mt-3 flex gap-2">
              <Button icon={<SkipBack className="h-4 w-4" strokeWidth={1.75} />} onClick={() => setStep((value) => Math.max(0, value - 1))}>Back</Button>
              <Button icon={<SkipForward className="h-4 w-4" strokeWidth={1.75} />} onClick={() => setStep((value) => Math.min(animalObservations.length - 1, value + 1))}>Next</Button>
              <Button icon={<RotateCcw className="h-4 w-4" strokeWidth={1.75} />} onClick={() => setStep(0)}>Reset</Button>
            </div>
          </div>
          <div className="divider-row grid grid-cols-2 rounded-panel border border-line">
            <div className="p-3"><div className="font-display text-2xl tabular">{formatDistanceKm(movement.data.total_distance_meters)}</div><div className="text-xs text-ink-600">Distance km</div></div>
            <div className="p-3"><div className="font-display text-2xl tabular">{formatDuration(movement.data.movement_duration_seconds)}</div><div className="text-xs text-ink-600">Duration</div></div>
            <div className="p-3"><div className="font-display text-2xl tabular">{new Set(animalObservations.map((item) => item.zoneId).filter(Boolean)).size}</div><div className="text-xs text-ink-600">Zones visited</div></div>
            <div className="p-3"><div className="font-display text-2xl tabular">{movement.data.point_count ?? animalObservations.length}</div><div className="text-xs text-ink-600">Route points</div></div>
          </div>
          <div className="rounded-panel border border-line p-3">
            <h3 className="text-sm font-medium text-ink-900">Observation window</h3>
            <dl className="mt-3 grid grid-cols-2 gap-3 text-sm">
              <div>
                <dt className="text-xs text-ink-400">First observation</dt>
                <dd className="font-mono text-xs tabular">{movement.data.started_at ? formatTime(movement.data.started_at) : "No observation"}</dd>
              </div>
              <div>
                <dt className="text-xs text-ink-400">Latest observation</dt>
                <dd className="font-mono text-xs tabular">{movement.data.ended_at ? formatTime(movement.data.ended_at) : "No observation"}</dd>
              </div>
            </dl>
          </div>
          <div className="rounded-panel border border-line p-3">
            <h3 className="text-sm font-medium text-ink-900">Zone timeline</h3>
            <div className="mt-3 space-y-2">
              {zoneHistory.data.segments.length ? zoneHistory.data.segments.map((segment, index) => <div key={`${segment.entered_at}-${index}`} className="flex items-center justify-between gap-3 text-sm">
                    <span className="truncate">{zoneLabel(segment.zone)}</span>
                    <span className="font-mono text-xs tabular text-ink-600">{formatDuration(segment.duration_seconds)}</span>
                  </div>) : <div className="text-sm text-ink-600">No zone history for this range.</div>}
            </div>
          </div>
          <div className="rounded-panel border border-line p-3">
            <h3 className="text-sm font-medium text-ink-900">Transitions</h3>
            <div className="mt-3 space-y-2">
              {zoneHistory.data.transitions.length ? zoneHistory.data.transitions.map((transition, index) => <div key={`${transition.transitioned_at}-${index}`} className="text-sm">
                    <div className="font-mono text-xs tabular text-ink-600">{formatTime(transition.transitioned_at)}</div>
                    <div className="truncate">{zoneLabel(transition.from_zone)} → {zoneLabel(transition.to_zone)}</div>
                  </div>) : <div className="text-sm text-ink-600">No zone transitions for this range.</div>}
            </div>
          </div>
          <div className="rounded-panel border border-line p-3">
            <h3 className="text-sm font-medium text-ink-900">Chronological timeline</h3>
            <div className="mt-3 max-h-44 space-y-2 overflow-auto pr-1">
              {timeline.data.events.length ? timeline.data.events.slice(0, 20).map((event, index) => <div key={`${event.timestamp}-${event.event_type}-${index}`} className="text-sm">
                    <div className="font-mono text-xs tabular text-ink-600">{formatTime(event.timestamp)}</div>
                    {event.event_type === "zone_transition" ? <div className="truncate">{zoneLabel(event.from_zone)} → {zoneLabel(event.to_zone)}</div> : <div className="truncate">{zoneLabel(event.zone)} · {formatDistanceKm(event.distance_from_previous_meters)} km from previous</div>}
                  </div>) : <div className="text-sm text-ink-600">No timeline events for this range.</div>}
            </div>
          </div>
        </div>
      </aside>
      <ForestMap
    animals={selectedSnapshot}
    devices={devices.data}
    zones={zones.data}
    boundary={boundary.data}
    alerts={alerts.data}
    movementPaths={path}
    selectedAnimalId={selectedAnimal.id}
    selectedMovementSummary={movement.data}
    className="h-full min-h-[620px]"
  />
    </div>;
};

export {
  MovementHistory
};
