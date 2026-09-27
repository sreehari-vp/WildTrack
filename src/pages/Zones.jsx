import { useEffect, useState } from "react";
import { RiskBadge } from "../components/animals/StatusBadge";
import { Select } from "../components/common/Select";
import { ZoneList } from "../components/zones/ZoneList";
import { useAlerts } from "../hooks/useAlerts";
import { useAnimals } from "../hooks/useAnimals";
import { useZoneAnimals, useZones, useZoneTransitions } from "../hooks/useZones";
import { formatTime } from "../utils/format";
import { zoneLabels } from "../utils/risk";
import { DataState } from "./PageState";
const Zones = () => {
  const [selectedZoneId, setSelectedZoneId] = useState();
  const zones = useZones();
  const animals = useAnimals();
  const alerts = useAlerts();
  const selectedZone = zones.data?.find((zone) => zone.id === selectedZoneId) ?? zones.data?.[0];
  const zoneAnimals = useZoneAnimals(selectedZone?.id);
  const zoneTransitions = useZoneTransitions(selectedZone?.id);
  const loading = zones.loading || animals.loading || alerts.loading || zoneAnimals.loading || zoneTransitions.loading;
  const error = zones.error || animals.error || alerts.error || zoneAnimals.error || zoneTransitions.error;
  useEffect(() => {
    if (!selectedZoneId && zones.data?.length) {
      setSelectedZoneId(zones.data[0].id);
    }
  }, [selectedZoneId, zones.data]);
  if (loading || error || !zones.data || !animals.data || !alerts.data || !zoneAnimals.data || !zoneTransitions.data) {
    return <div className="p-6"><DataState loading={loading} error={error} onRetry={() => window.location.reload()} /></div>;
  }
  return <div className="space-y-5 p-6">
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div><h2 className="font-display text-2xl">Zones</h2><p className="mt-1 text-sm text-ink-600">Read-only reserve zones and current operational load.</p></div>
        <div className="flex gap-2"><Select><option>All types</option></Select><Select><option>All risk</option></Select></div>
      </div>
      {selectedZone ? <section className="rounded-panel border border-line bg-paper p-4">
          <div className="flex flex-wrap items-start justify-between gap-4">
            <div>
              <div className="text-xs text-ink-400">{zoneLabels[selectedZone.type]} zone</div>
              <h3 className="font-display text-xl text-ink-900">{selectedZone.name}</h3>
              <p className="mt-1 max-w-3xl text-sm text-ink-600">{selectedZone.description}</p>
            </div>
            <RiskBadge risk={selectedZone.risk} />
          </div>
          <div className="mt-4 grid gap-4 md:grid-cols-[1fr_1.3fr]">
            <div>
              <div className="text-xs text-ink-400">Current animals</div>
              <div className="mt-2 flex flex-wrap gap-2">
                {zoneAnimals.data.length ? zoneAnimals.data.map((animal) => <span key={animal.id} className="rounded-control border border-line bg-moss-100 px-2 py-1 font-mono text-xs tabular">{animal.id}</span>) : <span className="text-sm text-ink-600">No tracked animals currently inside.</span>}
              </div>
            </div>
            <div>
              <div className="text-xs text-ink-400">Recent entries and exits</div>
              <div className="mt-2 space-y-2">
                {zoneTransitions.data.length ? zoneTransitions.data.slice(0, 4).map((transition, index) => <div key={`${transition.transitioned_at}-${index}`} className="flex items-center justify-between gap-3 text-sm">
                    <span className="truncate font-mono text-xs tabular">{transition.animal_code}</span>
                    <span className="truncate text-ink-600">{transition.from_zone?.name ?? "Outside reserve"} → {transition.to_zone?.name ?? "Outside reserve"}</span>
                    <span className="shrink-0 font-mono text-xs tabular text-ink-400">{formatTime(transition.transitioned_at)}</span>
                  </div>) : <div className="text-sm text-ink-600">No recent zone transitions in the current observation set.</div>}
              </div>
            </div>
          </div>
        </section> : null}
      <ZoneList zones={zones.data} animals={animals.data} alerts={alerts.data} selectedZoneId={selectedZone?.id} onSelectZone={(zone) => setSelectedZoneId(zone.id)} />
    </div>;
};
export {
  Zones
};
