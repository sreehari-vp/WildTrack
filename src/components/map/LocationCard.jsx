import { Copy } from "lucide-react";
import { useState } from "react";
import { formatCoordinate } from "../../utils/format";
import { riskMeta, zoneLabels } from "../../utils/risk";
import { Button } from "../common/Button";
const LocationCard = ({ location, onClose }) => {
  const [copied, setCopied] = useState(false);
  const risk = riskMeta[location.risk];
  const Icon = risk.Icon;
  const text = `${formatCoordinate(location.coordinates[1])}, ${formatCoordinate(location.coordinates[0])}`;
  return <div className="absolute left-20 top-36 z-30 w-72 rounded-panel border border-line bg-paper p-3 shadow-md">
      <div className="flex items-start justify-between">
        <div>
          <h3 className="font-medium text-ink-900">Location</h3>
          <p className="font-mono text-xs tabular text-ink-600">{text}</p>
        </div>
        <button className="text-ink-400" onClick={onClose} aria-label="Close location card">×</button>
      </div>
      <dl className="mt-3 space-y-2 text-sm">
        <div className="flex justify-between gap-3">
          <dt className="text-ink-400">Current zone</dt>
          <dd className="text-right text-ink-900">{location.zoneName ?? "Outside reserve"}</dd>
        </div>
        <div className="flex justify-between gap-3">
          <dt className="text-ink-400">Zone type</dt>
          <dd>{location.zoneType ? zoneLabels[location.zoneType] : "Unassigned"}</dd>
        </div>
        <div className="flex justify-between gap-3">
          <dt className="text-ink-400">Risk</dt>
          <dd className={`flex items-center gap-1 ${risk.className}`}>
            <Icon className="h-3.5 w-3.5" strokeWidth={1.75} />
            {risk.label}
          </dd>
        </div>
      </dl>
      <Button
    className="mt-4 w-full"
    icon={<Copy className="h-4 w-4" strokeWidth={1.75} />}
    onClick={() => {
      navigator.clipboard.writeText(text);
      setCopied(true);
    }}
  >
        {copied ? "Copied" : "Copy coordinates"}
      </Button>
    </div>;
};
export {
  LocationCard
};
