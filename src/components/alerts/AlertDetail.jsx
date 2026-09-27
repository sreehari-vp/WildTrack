import { MapPinned, PawPrint, RotateCcw } from "lucide-react";
import { useNavigate } from "react-router-dom";
import { formatCoordinate, formatTime, titleCase } from "../../utils/format";
import { Button } from "../common/Button";
import { SeverityBadge } from "./SeverityBadge";
const AlertDetail = ({
  alert,
  animal,
  zone,
  onResolve
}) => {
  const navigate = useNavigate();
  if (!alert) {
    return <div className="surface flex min-h-96 items-center justify-center p-8 text-sm text-ink-600">Select an alert to inspect details.</div>;
  }
  return <section className="surface p-5">
      <div className="flex items-start justify-between gap-4">
        <div>
          <SeverityBadge severity={alert.severity} />
          <h2 className="mt-3 font-display text-2xl text-ink-900">{alert.title}</h2>
          <p className="mt-1 text-sm text-ink-600">{alert.description}</p>
        </div>
        <span className="rounded-control border border-line px-2 py-1 text-xs text-ink-600">{titleCase(alert.status)}</span>
      </div>
      <dl className="mt-6 grid grid-cols-2 gap-x-8 gap-y-4 text-sm">
        <div><dt className="text-xs text-ink-400">Animal</dt><dd className="font-mono tabular">{animal?.id} · {animal?.name}</dd></div>
        <div><dt className="text-xs text-ink-400">Species</dt><dd>{animal ? titleCase(animal.species) : ""}</dd></div>
        <div><dt className="text-xs text-ink-400">Location</dt><dd>{zone?.name}</dd></div>
        <div><dt className="text-xs text-ink-400">Coordinates</dt><dd className="font-mono tabular">{animal ? `${formatCoordinate(animal.coordinates[1])}, ${formatCoordinate(animal.coordinates[0])}` : ""}</dd></div>
        <div><dt className="text-xs text-ink-400">Event</dt><dd>{titleCase(alert.type)}</dd></div>
        <div><dt className="text-xs text-ink-400">Trigger condition</dt><dd>{alert.trigger}</dd></div>
        <div><dt className="text-xs text-ink-400">Timestamp</dt><dd>{formatTime(alert.timestamp)}</dd></div>
        <div><dt className="text-xs text-ink-400">Status</dt><dd>{titleCase(alert.status)}</dd></div>
      </dl>
      <div className="mt-6 flex flex-wrap gap-2">
        <Button icon={<MapPinned className="h-4 w-4" strokeWidth={1.75} />} onClick={() => navigate(`/monitor?animal=${alert.animalId}`)}>View on map</Button>
        <Button icon={<PawPrint className="h-4 w-4" strokeWidth={1.75} />} onClick={() => navigate(`/animals/${alert.animalId}`)}>View animal</Button>
        <Button variant="primary" icon={<RotateCcw className="h-4 w-4" strokeWidth={1.75} />} onClick={onResolve} disabled={alert.status === "resolved"}>Resolve</Button>
      </div>
    </section>;
};
export {
  AlertDetail
};
