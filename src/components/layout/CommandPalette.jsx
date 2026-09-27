import { useEffect, useMemo, useState } from "react";
import { Search, X } from "lucide-react";
import { useNavigate } from "react-router-dom";
import { useAnimals } from "../../hooks/useAnimals";
import { useAlerts } from "../../hooks/useAlerts";
import { useZones } from "../../hooks/useZones";
import { Input } from "../common/Input";
const CommandPalette = ({ open, onClose }) => {
  const navigate = useNavigate();
  const { data: animals = [] } = useAnimals();
  const { data: zones = [] } = useZones();
  const { data: alerts = [] } = useAlerts();
  const [query, setQuery] = useState("");
  useEffect(() => {
    if (!open) setQuery("");
  }, [open]);
  const results = useMemo(() => {
    const q = query.trim().toLowerCase();
    const animalResults = animals.filter((animal) => [animal.id, animal.name, animal.species].join(" ").toLowerCase().includes(q)).slice(0, 5).map((animal) => ({ group: "Animals", label: `${animal.id} \xB7 ${animal.name}`, path: `/animals/${animal.id}` }));
    const zoneResults = zones.filter((zone) => [zone.name, zone.type].join(" ").toLowerCase().includes(q)).slice(0, 5).map((zone) => ({ group: "Zones", label: zone.name, path: `/monitor?zone=${zone.id}` }));
    const alertResults = alerts.filter((alert) => [alert.id, alert.title, alert.severity].join(" ").toLowerCase().includes(q)).slice(0, 5).map((alert) => ({ group: "Alerts", label: `${alert.id} \xB7 ${alert.title}`, path: `/alerts/${alert.id}` }));
    return q ? [...animalResults, ...zoneResults, ...alertResults] : [];
  }, [animals, alerts, query, zones]);
  if (!open) return null;
  return <div className="fixed inset-0 z-[900] bg-forest-950/20 p-4 backdrop-blur-sm" role="dialog" aria-modal="true">
      <div className="mx-auto mt-24 max-w-xl overflow-hidden rounded-panel border border-line bg-paper shadow-md">
        <div className="flex items-center gap-2 border-b border-line p-3">
          <Search className="h-4 w-4 text-ink-400" strokeWidth={1.75} />
          <Input
    autoFocus
    value={query}
    onChange={(event) => setQuery(event.target.value)}
    placeholder="Search animals, zones, alerts"
    className="border-0 bg-transparent focus-visible:outline-none"
    onKeyDown={(event) => {
      if (event.key === "Escape") onClose();
      if (event.key === "Enter" && results[0]) {
        navigate(results[0].path);
        onClose();
      }
    }}
  />
          <button aria-label="Close search" onClick={onClose}>
            <X className="h-4 w-4 text-ink-400" strokeWidth={1.75} />
          </button>
        </div>
        <div className="max-h-96 overflow-auto p-2">
          {results.length === 0 ? <p className="px-3 py-8 text-center text-sm text-ink-600">Type an animal ID, zone, or alert.</p> : results.map((result, index) => <button
    key={`${result.path}-${index}`}
    className="flex w-full items-center justify-between rounded-control px-3 py-2 text-left hover:bg-moss-100"
    onClick={() => {
      navigate(result.path);
      onClose();
    }}
  >
                <span className="text-sm text-ink-900">{result.label}</span>
                <span className="text-xs text-ink-400">{result.group}</span>
              </button>)}
        </div>
      </div>
    </div>;
};
export {
  CommandPalette
};
