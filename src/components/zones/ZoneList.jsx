import { MapPinned } from "lucide-react";
import { useNavigate } from "react-router-dom";
import { zoneLabels } from "../../utils/risk";
import { Button } from "../common/Button";
import { RiskBadge } from "../animals/StatusBadge";
const ZoneList = ({ zones, animals, alerts, selectedZoneId, onSelectZone }) => {
  const navigate = useNavigate();
  return <div className="overflow-hidden rounded-panel border border-line bg-paper">
      <table className="w-full border-collapse text-left text-sm">
        <thead className="border-b border-line text-xs text-ink-400">
          <tr>
            {["Name", "Type", "Risk", "Animals inside", "Recent alerts", "Area", ""].map((item) => <th key={item} className="px-4 py-3 font-medium">{item}</th>)}
          </tr>
        </thead>
        <tbody>
          {zones.map((zone) => <tr key={zone.id} className={`border-b border-line last:border-0 hover:bg-moss-100 ${selectedZoneId === zone.id ? "bg-moss-100" : ""}`} onClick={() => onSelectZone?.(zone)}>
              <td className="px-4 py-3"><div className="font-medium">{zone.name}</div><div className="text-xs text-ink-600">{zone.description}</div></td>
              <td className="px-4 py-3">{zoneLabels[zone.type]}</td>
              <td className="px-4 py-3"><RiskBadge risk={zone.risk} /></td>
              <td className="px-4 py-3 font-mono tabular">{animals.filter((animal) => animal.currentZoneId === zone.id).length}</td>
              <td className="px-4 py-3 font-mono tabular">{alerts.filter((alert) => alert.zoneId === zone.id).length}</td>
              <td className="px-4 py-3 font-mono tabular">{zone.areaKm2.toFixed(1)} km²</td>
              <td className="px-4 py-3 text-right"><Button icon={<MapPinned className="h-4 w-4" strokeWidth={1.75} />} onClick={(event) => {
                event.stopPropagation();
                navigate(`/monitor?zone=${zone.id}`);
              }}>View on map</Button></td>
            </tr>)}
        </tbody>
      </table>
    </div>;
};
export {
  ZoneList
};
