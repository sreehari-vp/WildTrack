import { useEffect, useMemo, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { AlertDetail } from "../components/alerts/AlertDetail";
import { AlertList } from "../components/alerts/AlertList";
import { Button } from "../components/common/Button";
import { Input } from "../components/common/Input";
import { Select } from "../components/common/Select";
import { useToast } from "../hooks/useToast";
import { useAlerts } from "../hooks/useAlerts";
import { useAnimals } from "../hooks/useAnimals";
import { useZones } from "../hooks/useZones";
import { alertService } from "../services/alertService";
import { DataState } from "./PageState";
const Alerts = () => {
  const { id } = useParams();
  const navigate = useNavigate();
  const { pushToast } = useToast();
  const alerts = useAlerts();
  const animals = useAnimals();
  const zones = useZones();
  const [localAlerts, setLocalAlerts] = useState([]);
  const [severity, setSeverity] = useState("all");
  const [status, setStatus] = useState("all");
  const [query, setQuery] = useState("");
  useEffect(() => {
    if (alerts.data) setLocalAlerts(alerts.data);
  }, [alerts.data]);
  const loading = alerts.loading || animals.loading || zones.loading;
  const error = alerts.error || animals.error || zones.error;
  const filtered = useMemo(
    () => localAlerts.filter((alert) => severity === "all" ? true : alert.severity === severity).filter((alert) => status === "all" ? true : alert.status === status).filter((alert) => [alert.id, alert.title, alert.animalId, alert.zoneId].join(" ").toLowerCase().includes(query.toLowerCase())),
    [localAlerts, query, severity, status]
  );
  if (loading || error || !animals.data || !zones.data) {
    return <div className="p-6"><DataState loading={loading} error={error} onRetry={() => window.location.reload()} /></div>;
  }
  const selected = localAlerts.find((alert) => alert.id === id) ?? filtered[0];
  const selectedAnimal = selected ? animals.data.find((animal) => animal.id === selected.animalId) : void 0;
  const selectedZone = selected ? zones.data.find((zone) => zone.id === selected.zoneId) : void 0;
  return <div className="grid h-[calc(100vh-56px)] grid-cols-[420px_minmax(0,1fr)] gap-6 p-6 max-lg:grid-cols-1 max-lg:h-auto">
      <aside className="min-h-0 space-y-3">
        <div><h2 className="font-display text-2xl">Alerts</h2><p className="mt-1 text-sm text-ink-600">Review active and acknowledged field alerts.</p></div>
        <div className="flex flex-wrap gap-2">
          <Input placeholder="Search alerts" value={query} onChange={(event) => setQuery(event.target.value)} />
          <Select value={severity} onChange={(event) => setSeverity(event.target.value)}><option value="all">All severity</option><option value="info">Info</option><option value="low">Low</option><option value="medium">Medium</option><option value="high">High</option><option value="critical">Critical</option></Select>
          <Select value={status} onChange={(event) => setStatus(event.target.value)}><option value="all">All status</option><option value="open">Open</option><option value="acknowledged">Acknowledged</option><option value="resolved">Resolved</option></Select>
          <Button variant="ghost" onClick={() => {
    setQuery("");
    setSeverity("all");
    setStatus("all");
  }}>Clear filters</Button>
        </div>
        <div className="max-h-[calc(100vh-210px)] overflow-auto max-lg:max-h-none">
          <AlertList alerts={filtered} animals={animals.data} zones={zones.data} selectedId={selected?.id} onSelect={(alert) => navigate(`/alerts/${alert.id}`)} />
        </div>
      </aside>
      <AlertDetail
    alert={selected}
    animal={selectedAnimal}
    zone={selectedZone}
    onResolve={async () => {
      if (!selected) return;
      try {
        const resolved = await alertService.resolveAlert(selected.id);
        setLocalAlerts((current) => current.map((alert) => alert.id === selected.id ? resolved : alert));
        pushToast({ title: "Alert resolved" });
      } catch {
        pushToast({ title: "Could not resolve alert" });
      }
    }}
  />
    </div>;
};
export {
  Alerts
};
