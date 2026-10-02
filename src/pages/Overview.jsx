import { useNavigate } from "react-router-dom";
import { Bar, BarChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { AlertList } from "../components/alerts/AlertList";
import { ChartPanel } from "../components/analytics/ChartPanel";
import { ForestMap } from "../components/map/ForestMap";
import { useAlerts } from "../hooks/useAlerts";
import { useAnalytics } from "../hooks/useAnalytics";
import { useAnimals } from "../hooks/useAnimals";
import { useBoundary, useZones } from "../hooks/useZones";
import { useDevices } from "../hooks/useDevices";
import { useObservations } from "../hooks/useObservations";
import { movementPathsFromObservations } from "../utils/movement";
import { DataState } from "./PageState";
import { WildTrackLoader } from "../components/common/WildTrackLoader";
const Overview = () => {
  const navigate = useNavigate();
  const animals = useAnimals();
  const zones = useZones();
  const alerts = useAlerts();
  const boundary = useBoundary();
  const devices = useDevices();
  const observations = useObservations();
  const analytics = useAnalytics();
  const loading = animals.loading || zones.loading || alerts.loading || boundary.loading || devices.loading || observations.loading;
  const error = animals.error || zones.error || alerts.error || boundary.error || devices.error || observations.error;
  const openAlerts = (alerts.data ?? []).filter((alert) => alert.status !== "resolved");
  const figures = [
    ["Total animals", animals.data?.length ?? 0],
    ["Active", animals.data?.filter((animal) => animal.status === "active").length ?? 0],
    ["Active alerts", openAlerts.length],
    ["High-risk animals", animals.data?.filter((animal) => animal.risk === "high" || animal.risk === "critical").length ?? 0],
    ["Zones monitored", zones.data?.length ?? 0]
  ];
  const state = <DataState loading={loading} error={error} onRetry={() => window.location.reload()} />;
  if (loading || error || !animals.data || !zones.data || !alerts.data || !boundary.data || !devices.data || !observations.data) {
    return <div className="p-6">{state}</div>;
  }
  const zoneData = zones.data;
  const zoneCounts = zoneData.reduce((acc, zone) => ({ ...acc, [zone.type]: (acc[zone.type] ?? 0) + 1 }), {});
  return <div className="space-y-6 p-6">
      <section className="divider-row grid grid-cols-2 rounded-panel border border-line bg-paper md:grid-cols-5">
        {figures.map(([label, value]) => <div key={label} className="p-4">
            <div className="font-display text-4xl tabular">{value}</div>
            <div className="text-xs text-ink-600">{label}</div>
          </div>)}
      </section>
      <div className="grid gap-6 xl:grid-cols-[minmax(0,1.45fr)_minmax(360px,0.9fr)]">
        <button className="min-h-[520px] overflow-hidden rounded-panel border border-line text-left" onClick={() => navigate("/monitor")} aria-label="Open live monitor">
          <ForestMap animals={animals.data} devices={devices.data} zones={zoneData} boundary={boundary.data} alerts={alerts.data} movementPaths={movementPathsFromObservations(observations.data)} alertsOpenAnimalIds={openAlerts.map((alert) => alert.animalId)} preview className="h-full min-h-[520px]" />
        </button>
        <div className="space-y-6">
          <section>
            <h2 className="mb-3 font-medium">Recent alerts</h2>
            <AlertList alerts={alerts.data.slice(0, 5)} animals={animals.data} zones={zoneData} onSelect={(alert) => navigate(`/alerts/${alert.id}`)} />
          </section>
          <section className="surface p-4">
            <h2 className="mb-3 font-medium">Zone risk summary</h2>
            <div className="flex h-4 overflow-hidden rounded-control border border-line">
              {Object.entries(zoneCounts).map(([type, count]) => <span key={type} style={{ width: `${count / zoneData.length * 100}%`, background: `var(--${type === "protected" ? "zone-protected" : type === "safe" ? "risk-safe" : type === "buffer" ? "risk-medium" : type === "water-source" ? "risk-info" : type === "restricted" ? "risk-high" : "risk-critical"})` }} />)}
            </div>
            <div className="mt-3 flex flex-wrap gap-3 text-xs text-ink-600">
              {Object.entries(zoneCounts).map(([type, count]) => <span key={type}>{type.replace("-", " ")} · {count}</span>)}
            </div>
          </section>
        </div>
      </div>
      <ChartPanel title="Animal activity">
        {analytics.loading ? <div className="flex h-64 items-center justify-center"><WildTrackLoader compact /></div> : analytics.error ? <div className="flex h-64 items-center justify-center text-sm text-ink-600">Activity data unavailable</div> : <div className="h-64">
            <ResponsiveContainer>
              <BarChart data={analytics.data?.hourlyActivity ?? []}>
                <XAxis dataKey="hour" tickLine={false} axisLine={false} />
                <YAxis tickLine={false} axisLine={false} />
                <Tooltip />
                <Bar dataKey="elephants" fill="var(--forest-700)" />
                <Bar dataKey="tigers" fill="var(--risk-high)" />
                <Bar dataKey="deer" fill="var(--risk-safe)" />
              </BarChart>
            </ResponsiveContainer>
          </div>}
      </ChartPanel>
    </div>;
};
export {
  Overview
};
