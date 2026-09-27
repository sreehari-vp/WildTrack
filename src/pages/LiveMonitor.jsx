import { useState } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
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
import { movementPathsFromObservations } from "../utils/movement";
import { DataState } from "./PageState";
const LiveMonitor = () => {
  const pollingMs = Number(import.meta.env.VITE_API_POLLING_INTERVAL_MS ?? 5e3);
  const [tab, setTab] = useState("alerts");
  const [panelOpen, setPanelOpen] = useState(true);
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const animals = useAnimals(pollingMs);
  const zones = useZones();
  const alerts = useAlerts();
  const boundary = useBoundary();
  const devices = useDevices(pollingMs);
  const observations = useObservations(pollingMs);
  const selectedAnimalId = searchParams.get("animal") ?? void 0;
  const selectedMovement = useMovementForAnimal(selectedAnimalId, { limit: 500 });
  const loading = animals.loading || zones.loading || alerts.loading || boundary.loading || devices.loading || observations.loading;
  const error = animals.error || zones.error || alerts.error || boundary.error || devices.error || observations.error;
  const state = <DataState loading={loading} error={error} onRetry={() => window.location.reload()} />;
  if (loading || error || !animals.data || !zones.data || !alerts.data || !boundary.data || !devices.data || !observations.data) {
    return <div className="p-6">{state}</div>;
  }
  const openAlerts = alerts.data.filter((alert) => alert.status !== "resolved");
  const selectedAnimal = selectedAnimalId ?? animals.data.find((animal) => animal.id === selectedAnimalId)?.id;
  return <div className="relative h-[calc(100vh-56px)]">
      <ForestMap animals={animals.data} devices={devices.data} zones={zones.data} boundary={boundary.data} alerts={alerts.data} movementPaths={movementPathsFromObservations(observations.data)} alertsOpenAnimalIds={openAlerts.map((alert) => alert.animalId)} selectedAnimalId={selectedAnimal} selectedMovementSummary={selectedMovement.data} className="h-full" />
      {panelOpen ? <aside className="absolute right-4 top-4 z-30 flex max-h-[calc(100%-32px)] w-[340px] flex-col rounded-panel border border-line bg-paper/95 shadow-md max-md:bottom-4 max-md:top-auto max-md:w-[calc(100%-32px)]">
          <div className="flex items-center justify-between border-b border-line p-3">
            <div className="flex rounded-control border border-line p-1">
              <button className={`rounded-control px-3 py-1 text-sm ${tab === "alerts" ? "bg-forest-700 text-paper" : "text-ink-600"}`} onClick={() => setTab("alerts")}>Alerts</button>
              <button className={`rounded-control px-3 py-1 text-sm ${tab === "animals" ? "bg-forest-700 text-paper" : "text-ink-600"}`} onClick={() => setTab("animals")}>Animals</button>
            </div>
            <Button variant="ghost" onClick={() => setPanelOpen(false)}>Collapse</Button>
          </div>
          <div className="overflow-auto p-3">
            {tab === "alerts" ? <AlertList alerts={openAlerts} animals={animals.data} zones={zones.data} onSelect={(alert) => navigate(`/monitor?animal=${alert.animalId}`)} /> : <div className="divide-y divide-line rounded-panel border border-line bg-paper">
                {animals.data.slice(0, 14).map((animal) => <button key={animal.id} className="flex w-full items-center gap-3 px-3 py-3 text-left hover:bg-moss-100" onClick={() => navigate(`/monitor?animal=${animal.id}`)}>
                    <SpeciesIcon species={animal.species} className="h-5 w-5" />
                    <div className="min-w-0 flex-1"><div className="font-mono text-sm tabular">{animal.id}</div><div className="truncate text-xs text-ink-600">{animal.name}</div></div>
                    <StatusBadge status={animal.status} />
                    <RiskBadge risk={animal.risk} />
                  </button>)}
              </div>}
          </div>
        </aside> : <Button className="absolute right-4 top-4 z-30 shadow-md" onClick={() => setPanelOpen(true)}>Open panel</Button>}
    </div>;
};
export {
  LiveMonitor
};
