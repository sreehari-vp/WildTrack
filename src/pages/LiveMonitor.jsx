import { useEffect, useState } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import { Play, Square } from "lucide-react";
import { AlertList } from "../components/alerts/AlertList";
import { RiskBadge, StatusBadge } from "../components/animals/StatusBadge";
import { SpeciesIcon } from "../components/animals/SpeciesIcon";
import { Button } from "../components/common/Button";
import { ForestMap } from "../components/map/ForestMap";
import { useAlerts } from "../hooks/useAlerts";
import { useAnimals } from "../hooks/useAnimals";
import { useDevices } from "../hooks/useDevices";
import { useMovementForAnimal, useObservations } from "../hooks/useObservations";
import { useBoundary, useZones } from "../hooks/useZones";
import { useAsyncData } from "../hooks/useAsyncData";
import { useToast } from "../hooks/useToast";
import { monitoringService } from "../services/monitoringService";
import { apiUrl } from "../services/apiClient";
import { movementPathsFromObservations } from "../utils/movement";
import { DataState } from "./PageState";
const LiveMonitor = () => {
  const pollingMs = Number(import.meta.env.VITE_API_POLLING_INTERVAL_MS ?? 3e3);
  const [tab, setTab] = useState("alerts");
  const [panelOpen, setPanelOpen] = useState(false);
  const [simulationBusy, setSimulationBusy] = useState(false);
  const { pushToast } = useToast();
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const animals = useAnimals(pollingMs);
  const zones = useZones();
  const alerts = useAlerts(pollingMs);
  const boundary = useBoundary();
  const devices = useDevices(pollingMs);
  const observations = useObservations(pollingMs);
  const simulation = useAsyncData(monitoringService.getSimulationStatus, [], { intervalMs: pollingMs });
  const summary = useAsyncData(monitoringService.getSummary, [], { intervalMs: Math.max(pollingMs, 10000) });
  useEffect(() => {
    const stream = new EventSource(apiUrl("/monitoring/stream"));
    stream.addEventListener("update", () => {
      Promise.allSettled([
        animals.refresh(), alerts.refresh(), devices.refresh(), observations.refresh(), summary.refresh()
      ]);
    });
    return () => stream.close();
  }, [animals.refresh, alerts.refresh, devices.refresh, observations.refresh, summary.refresh]);
  const changeSimulation = async () => {
    if (simulationBusy) return;
    setSimulationBusy(true);
    try {
      if (simulation.data?.running) await monitoringService.stopSimulation();
      else await monitoringService.startSimulation();
      await Promise.allSettled([
        simulation.refresh(), animals.refresh(), devices.refresh(), observations.refresh(), alerts.refresh(), summary.refresh()
      ]);
    } catch (error) { pushToast({ title: `Simulator action failed: ${error.message}` }); }
    finally { setSimulationBusy(false); }
  };
  const selectedAnimalId = searchParams.get("animal") ?? void 0;
  const selectedMovement = useMovementForAnimal(selectedAnimalId, { limit: 500 });
  const loading = animals.loading || zones.loading || alerts.loading || boundary.loading || devices.loading || observations.loading;
  const error = animals.error || zones.error || alerts.error || boundary.error || devices.error || observations.error;
  const state = <DataState loading={loading} error={error} onRetry={() => window.location.reload()} />;
  if (loading || error || !animals.data || !zones.data || !alerts.data || !boundary.data || !devices.data || !observations.data) {
    return <div className="p-6">{state}</div>;
  }
  const openAlerts = alerts.data.filter((alert) => alert.status !== "resolved");
  const simulatorNeedsRestart = simulation.data && simulation.data.total_routes === undefined;
  const routeCount = simulation.data?.total_routes ?? 0;
  const completedRoutes = simulation.data?.completed_routes ?? 0;
  const movingCount = Math.max(routeCount - completedRoutes, 0);
  const simulationState = simulation.error ? "Simulator unavailable" : simulatorNeedsRestart ? "Restart backend to load journeys" : simulation.loading && !simulation.data ? "Checking simulator…" : simulation.data?.finished ? "All journeys complete" : simulation.data?.running ? `${movingCount} animals moving` : "Journeys paused";
  const selectedAnimal = selectedAnimalId;
  return <div className="relative h-[calc(100dvh-108px)]">
      <ForestMap animals={animals.data} devices={devices.data} zones={zones.data} onZonesChanged={zones.refresh} boundary={boundary.data} alerts={alerts.data} movementPaths={movementPathsFromObservations(observations.data)} alertsOpenAnimalIds={openAlerts.map((alert) => alert.animalId)} hideAlertSummary selectedAnimalId={selectedAnimal} selectedZoneId={searchParams.get("zone")} onAnimalSelect={(animal) => navigate(`/monitor?animal=${animal.id}`)} selectedMovementSummary={selectedMovement.data} className="h-full" />
      {panelOpen ? <aside className="absolute right-4 top-4 z-30 flex max-h-[calc(100%-32px)] w-[340px] flex-col rounded-panel border border-line bg-paper/95 shadow-md max-md:bottom-4 max-md:top-auto max-md:w-[calc(100%-32px)]">
          <div className="flex items-center justify-between border-b border-line p-3">
            <div className="flex rounded-control border border-line p-1">
              <button className={`rounded-control px-3 py-1 text-sm ${tab === "alerts" ? "bg-forest-700 text-paper" : "text-ink-600"}`} onClick={() => setTab("alerts")}>Alerts</button>
              <button className={`rounded-control px-3 py-1 text-sm ${tab === "animals" ? "bg-forest-700 text-paper" : "text-ink-600"}`} onClick={() => setTab("animals")}>Animals</button>
              <button className={`rounded-control px-3 py-1 text-sm ${tab === "status" ? "bg-forest-700 text-paper" : "text-ink-600"}`} onClick={() => setTab("status")}>Status</button>
            </div>
            <Button variant="ghost" onClick={() => setPanelOpen(false)}>Collapse</Button>
          </div>
          <div className="overflow-auto p-3">
            {tab === "alerts" ? <AlertList alerts={openAlerts} animals={animals.data} zones={zones.data} onSelect={(alert) => navigate(`/monitor?animal=${alert.animalId}`)} /> : tab === "status" ? <div className="space-y-3 text-sm">
                {summary.error ? <p>Monitoring summary unavailable: {summary.error.message}</p> : summary.data ? <>
                    <div className="grid grid-cols-2 gap-2">
                      <div className="rounded-control border border-line p-2"><div className="text-xs text-ink-600">Active animals</div><strong>{summary.data.counts.active_animals}</strong></div>
                      <div className="rounded-control border border-line p-2"><div className="text-xs text-ink-600">Open alerts</div><strong>{summary.data.counts.open_alerts}</strong></div>
                      <div className="rounded-control border border-line p-2"><div className="text-xs text-ink-600">Events awaiting MongoDB</div><strong>{summary.data.counts.pending_events}</strong></div>
                      <div className="rounded-control border border-line p-2"><div className="text-xs text-ink-600">Events retrying</div><strong>{summary.data.counts.retrying_events}</strong></div>
                    </div>
                    <p className="text-xs text-ink-600">Latest GPS: {summary.data.counts.latest_observation_at ? new Date(summary.data.counts.latest_observation_at).toLocaleString() : "Unknown"}</p>
                    <div className="border-t border-line pt-2 text-xs font-medium">Recent hourly activity</div>
                    {summary.data.hourly.slice(0, 6).map((hour) => <div key={hour.bucket_start} className="flex justify-between text-xs"><span>{new Date(hour.bucket_start).toLocaleString()}</span><span>{hour.observation_count} GPS · {hour.alert_count} alerts</span></div>)}
                </> : <p>Loading monitoring summary…</p>}
              </div> : <div className="divide-y divide-line rounded-panel border border-line bg-paper">
                {animals.data.map((animal) => <button key={animal.id} className="flex w-full items-center gap-3 px-3 py-3 text-left hover:bg-moss-100" onClick={() => navigate(`/monitor?animal=${animal.id}`)}>
                    <SpeciesIcon species={animal.species} className="h-5 w-5" />
                    <div className="min-w-0 flex-1"><div className="font-mono text-sm tabular">{animal.id}</div><div className="truncate text-xs text-ink-600">{animal.name}</div></div>
                    <StatusBadge status={animal.status} />
                    <RiskBadge risk={animal.risk} />
                  </button>)}
              </div>}
          </div>
        </aside> : <Button className="absolute right-4 top-4 z-30 shadow-md" onClick={() => setPanelOpen(true)}>Alerts {openAlerts.length ? `(${openAlerts.length})` : ""} / Animals</Button>}
      <div className="pointer-events-none absolute inset-x-3 bottom-4 z-40 flex justify-center">
        <section aria-label="Movement simulation controls" className="pointer-events-auto w-full max-w-[560px] overflow-hidden rounded-panel border border-line bg-paper/95 shadow-md backdrop-blur-md">
          <div className="flex items-center gap-3 px-4 py-3 sm:gap-5 sm:px-5">
            <span className={`relative flex h-3 w-3 shrink-0 rounded-full ${simulation.data?.running ? "bg-forest-500" : "bg-ink-400"}`} aria-hidden="true">
              {simulation.data?.running && <span className="absolute inset-0 animate-ping rounded-full bg-forest-500 opacity-40" />}
            </span>
            <div className="min-w-0 flex-1" aria-live="polite">
              <div className="text-xs font-semibold uppercase tracking-wide text-ink-600">Movement simulation</div>
              <div className="truncate text-sm font-semibold text-ink-900">{simulationState}</div>
              <div className="text-xs text-ink-600">{routeCount ? `${completedRoutes}/${routeCount} journeys complete · ` : ""}{simulation.data?.interval_seconds ? `GPS every ${simulation.data.interval_seconds} seconds` : "Waiting for backend"}</div>
            </div>
            <Button variant={simulation.data?.running ? "secondary" : "primary"} className="min-w-24 shrink-0" icon={simulation.data?.running ? <Square size={14} fill="currentColor" /> : <Play size={16} fill="currentColor" />} disabled={simulationBusy || simulation.loading || !!simulation.error || !!simulatorNeedsRestart || !!simulation.data?.finished || !simulation.data} onClick={changeSimulation}>{simulationBusy ? "Working…" : simulation.data?.running ? "Stop" : "Start"}</Button>
          </div>
          {routeCount > 0 && <div role="progressbar" aria-label="Completed animal journeys" aria-valuemin={0} aria-valuemax={routeCount} aria-valuenow={completedRoutes} className="h-1 bg-moss-100"><div className="h-full bg-forest-500 transition-[width] duration-500" style={{ width: `${completedRoutes / routeCount * 100}%` }} /></div>}
        </section>
      </div>
    </div>;
};
export {
  LiveMonitor
};
