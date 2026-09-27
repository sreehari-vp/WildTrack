import { ArrowDownUp, BatteryWarning } from "lucide-react";
import { useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import { formatRelative, titleCase } from "../../utils/format";
import { Input } from "../common/Input";
import { Select } from "../common/Select";
import { Button } from "../common/Button";
import { SpeciesIcon } from "./SpeciesIcon";
import { RiskBadge, StatusBadge } from "./StatusBadge";
const AnimalTable = ({ animals, devices, zones }) => {
  const navigate = useNavigate();
  const [query, setQuery] = useState("");
  const [species, setSpecies] = useState("all");
  const [status, setStatus] = useState("all");
  const [risk, setRisk] = useState("all");
  const [zone, setZone] = useState("all");
  const [sortKey, setSortKey] = useState("id");
  const filtered = useMemo(() => {
    return animals.filter((animal) => [animal.id, animal.name, animal.species].join(" ").toLowerCase().includes(query.toLowerCase())).filter((animal) => species === "all" ? true : animal.species === species).filter((animal) => status === "all" ? true : animal.status === status).filter((animal) => risk === "all" ? true : animal.risk === risk).filter((animal) => zone === "all" ? true : animal.currentZoneId === zone).sort((a, b) => {
      if (sortKey === "battery") {
        const aBattery = devices.find((device) => device.id === a.deviceId)?.battery ?? 0;
        const bBattery = devices.find((device) => device.id === b.deviceId)?.battery ?? 0;
        return aBattery - bBattery;
      }
      return String(a[sortKey]).localeCompare(String(b[sortKey]));
    });
  }, [animals, devices, query, risk, sortKey, species, status, zone]);
  return <div className="space-y-4">
      <div className="flex flex-wrap items-center gap-2">
        <Input className="w-64" placeholder="Search animal ID or tag" value={query} onChange={(event) => setQuery(event.target.value)} />
        <Select value={species} onChange={(event) => setSpecies(event.target.value)}><option value="all">All species</option><option value="elephant">Elephants</option><option value="tiger">Tigers</option><option value="deer">Deer</option></Select>
        <Select value={status} onChange={(event) => setStatus(event.target.value)}><option value="all">All status</option><option value="active">Active</option><option value="idle">Idle</option><option value="offline">Offline</option></Select>
        <Select value={risk} onChange={(event) => setRisk(event.target.value)}><option value="all">All risk</option><option value="safe">Safe</option><option value="medium">Medium</option><option value="high">High</option><option value="critical">Critical</option><option value="info">Info</option></Select>
        <Select value={zone} onChange={(event) => setZone(event.target.value)}><option value="all">All zones</option>{zones.map((item) => <option key={item.id} value={item.id}>{item.name}</option>)}</Select>
        <Button variant="ghost" onClick={() => {
    setQuery("");
    setSpecies("all");
    setStatus("all");
    setRisk("all");
    setZone("all");
  }}>Clear filters</Button>
      </div>
      <div className="overflow-hidden rounded-panel border border-line bg-paper">
        <table className="w-full border-collapse text-left text-sm">
          <thead className="border-b border-line text-xs text-ink-400">
            <tr>
              {["Animal", "Species", "Status", "Current zone", "Risk", "Last seen", "Battery"].map((header) => <th key={header} className="px-4 py-3 font-medium">
                  <button className="flex items-center gap-1" onClick={() => setSortKey(header === "Battery" ? "battery" : header === "Last seen" ? "lastSeen" : "id")}>
                    {header}<ArrowDownUp className="h-3 w-3" strokeWidth={1.75} />
                  </button>
                </th>)}
            </tr>
          </thead>
          <tbody>
            {filtered.map((animal) => {
    const device = devices.find((item) => item.id === animal.deviceId);
    const currentZone = zones.find((item) => item.id === animal.currentZoneId);
    const low = (device?.battery ?? 100) < 25;
    return <tr key={animal.id} className="cursor-pointer border-b border-line last:border-0 hover:bg-moss-100" onClick={() => navigate(`/animals/${animal.id}`)}>
                  <td className="px-4 py-3">
                    <div className="font-mono font-medium tabular">{animal.id}</div>
                    <div className="text-xs text-ink-600">{animal.name}</div>
                  </td>
                  <td className="px-4 py-3"><span className="flex items-center gap-2"><SpeciesIcon species={animal.species} className="h-4 w-4" />{titleCase(animal.species)}</span></td>
                  <td className="px-4 py-3"><StatusBadge status={animal.status} /></td>
                  <td className="px-4 py-3 text-ink-600">{currentZone?.name}</td>
                  <td className="px-4 py-3"><RiskBadge risk={animal.risk} /></td>
                  <td className="px-4 py-3 text-ink-600">{formatRelative(animal.lastSeen)}</td>
                  <td className="px-4 py-3">
                    <div className="flex items-center gap-2">
                      {low ? <BatteryWarning className="h-4 w-4 text-[color:var(--risk-medium)]" strokeWidth={1.75} /> : null}
                      <div className="battery-bar" data-low={low}><span style={{ width: `${device?.battery ?? 0}%` }} /></div>
                      <span className="font-mono text-xs tabular">{device?.battery}%</span>
                    </div>
                  </td>
                </tr>;
  })}
          </tbody>
        </table>
      </div>
    </div>;
};
export {
  AnimalTable
};
