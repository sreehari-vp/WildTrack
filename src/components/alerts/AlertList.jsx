import { formatTime } from "../../utils/format";
import { SeverityBadge } from "./SeverityBadge";
const AlertList = ({
  alerts,
  animals,
  zones,
  selectedId,
  onSelect
}) => <div className="divide-y divide-line overflow-hidden rounded-panel border border-line bg-paper">
    {alerts.map((alert) => {
  const animal = animals.find((item) => item.id === alert.animalId);
  const zone = zones.find((item) => item.id === alert.zoneId);
  return <button
    key={alert.id}
    className={`w-full px-4 py-3 text-left hover:bg-moss-100 ${selectedId === alert.id ? "bg-moss-100" : ""}`}
    onClick={() => onSelect(alert)}
  >
          <div className="flex items-start justify-between gap-3">
            <div className="min-w-0">
              <p className="truncate font-medium text-ink-900">{alert.title}</p>
              <p className="mt-1 truncate text-xs text-ink-600">
                {animal?.id} · {zone?.name} · {formatTime(alert.timestamp)}
              </p>
            </div>
            <SeverityBadge severity={alert.severity} />
          </div>
        </button>;
})}
  </div>;
export {
  AlertList
};
