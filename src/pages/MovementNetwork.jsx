import { useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { ArrowRight, GitBranch, RefreshCw, ShieldAlert } from "lucide-react";
import { Button } from "../components/common/Button";
import { Select } from "../components/common/Select";
import { useAsyncData } from "../hooks/useAsyncData";
import { networkService } from "../services/networkService";
import { DataState } from "./PageState";

const riskColor = {
  safe: "#3f8f5b", info: "#4b7f9e", low: "#6d9b5f",
  medium: "#c99a2e", high: "#d9691f", critical: "#c2362f"
};

const cutoff = (days) => {
  if (days === "all") return null;
  return new Date(Date.now() - Number(days) * 86400000).toISOString().slice(0, 10);
};

const layoutZones = (zones, corridors) => {
  const degree = new Map(zones.map((zone) => [zone.zone_id, 0]));
  corridors.forEach((corridor) => {
    degree.set(corridor.from_zone_id, (degree.get(corridor.from_zone_id) ?? 0) + corridor.crossings);
    degree.set(corridor.to_zone_id, (degree.get(corridor.to_zone_id) ?? 0) + corridor.crossings);
  });
  const ordered = [...zones].sort((a, b) => (degree.get(b.zone_id) ?? 0) - (degree.get(a.zone_id) ?? 0) || a.name.localeCompare(b.name));
  return new Map(ordered.map((zone, index) => {
    const angle = -Math.PI / 2 + index * Math.PI * 2 / Math.max(ordered.length, 1);
    return [zone.zone_id, { x: 500 + Math.cos(angle) * 335, y: 300 + Math.sin(angle) * 215 }];
  }));
};

const curve = (a, b) => {
  const dx = b.x - a.x;
  const dy = b.y - a.y;
  const length = Math.hypot(dx, dy) || 1;
  const nx = -dy / length;
  const ny = dx / length;
  const ux = dx / length;
  const uy = dy / length;
  return `M ${a.x + ux * 29} ${a.y + uy * 29} Q ${(a.x + b.x) / 2 + nx * 25} ${(a.y + b.y) / 2 + ny * 25} ${b.x - ux * 33} ${b.y - uy * 33}`;
};

const label = (value) => value ? new Date(value).toLocaleString() : "Unknown";

export const MovementNetwork = () => {
  const [species, setSpecies] = useState("");
  const [days, setDays] = useState("30");
  const [selected, setSelected] = useState(null);
  const [hovered, setHovered] = useState(null);
  const [view, setView] = useState("routes");
  const [detail, setDetail] = useState({ loading: false, data: null, error: null });
  const [syncBusy, setSyncBusy] = useState(false);
  const [syncError, setSyncError] = useState("");
  const [detailRevision, setDetailRevision] = useState(0);
  const filters = useMemo(() => ({ species, start_date: cutoff(days) }), [species, days]);
  const network = useAsyncData(() => networkService.getSnapshot(filters), [species, days], { intervalMs: 30000 });
  const zones = network.data?.zones ?? [];
  const corridors = network.data?.corridors ?? [];
  const positions = useMemo(() => layoutZones(zones, corridors), [zones, corridors]);
  const byId = useMemo(() => new Map(zones.map((zone) => [zone.zone_id, zone])), [zones]);
  const rankedCorridors = useMemo(
    () => [...corridors].sort((a, b) => b.crossings - a.crossings),
    [corridors]
  );
  const maxCrossings = rankedCorridors[0]?.crossings || 1;
  const focus = hovered ?? selected;
  const focusZones = focus?.kind === "corridor"
    ? new Set([focus.from, focus.to])
    : focus?.kind === "zone"
      ? new Set([focus.zone_id])
      : null;

  useEffect(() => {
    if (!selected || !network.data?.ready) {
      setDetail({ loading: false, data: null, error: null });
      return;
    }
    let active = true;
    setDetail({ loading: true, data: null, error: null });
    const request = selected.kind === "corridor"
      ? networkService.getCorridor(selected.from, selected.to, filters)
      : networkService.getImpact(selected.zone_id);
    request.then((data) => { if (active) setDetail({ loading: false, data, error: null }); })
      .catch((error) => { if (active) setDetail({ loading: false, data: null, error }); });
    return () => { active = false; };
  }, [selected, species, days, detailRevision, network.data?.ready]);

  const synchronize = async () => {
    setSyncBusy(true);
    setSyncError("");
    try {
      await networkService.sync();
      network.retry();
      setDetailRevision((value) => value + 1);
    } catch (error) {
      setSyncError(error.message);
    } finally {
      setSyncBusy(false);
    }
  };

  const selectedKey = selected?.kind === "corridor" ? `${selected.from}|${selected.to}` : null;
  const impacted = new Set(detail.data?.reachable_zones?.map((zone) => zone.zone_id) ?? []);
  const affectedEdges = selected?.kind === "zone" && detail.data?.origin_zone_id === selected.zone_id
    ? detail.data.corridors ?? []
    : [];
  const impactedCorridors = new Set(affectedEdges.map((edge) => `${edge.from_zone_id}|${edge.to_zone_id}`));
  const impactedZoneIds = new Set(affectedEdges.flatMap((edge) => [edge.from_zone_id, edge.to_zone_id]));
  return <div className="space-y-5 p-6">
    <div className="flex flex-wrap items-start justify-between gap-4">
      <div>
        <h2 className="font-display text-2xl">Movement Network</h2>
        <p className="mt-1 max-w-3xl text-sm text-ink-600">Observed connections between zones. This is a network of movements, not a map of exact trails.</p>
      </div>
      <Button onClick={synchronize} disabled={syncBusy || !network.data?.configured} icon={<RefreshCw className="h-4 w-4" />}>
        {syncBusy ? "Updating network…" : "Sync from PostgreSQL"}
      </Button>
    </div>

    {syncError ? <div className="rounded-panel border border-orange-200 bg-orange-50 p-3 text-sm text-orange-900">{syncError}</div> : null}
    {network.loading || network.error ? <DataState loading={network.loading} error={network.error} onRetry={network.retry} /> : null}
    {!network.loading && !network.error && !network.data?.configured ? <div className="rounded-panel border border-line bg-paper p-6">
      <h3 className="font-display text-xl">Connect Neo4j AuraDB Free</h3>
      <p className="mt-2 max-w-2xl text-sm text-ink-600">Create an AuraDB Free instance, add its NEO4J_URI, NEO4J_USERNAME and NEO4J_PASSWORD to the backend .env file, then restart the backend. Credentials stay on the backend.</p>
    </div> : null}
    {!network.loading && !network.error && network.data?.configured && !network.data?.ready ? <div className="rounded-panel border border-line bg-paper p-6">
      <h3 className="font-display text-xl">The network is waiting for its first sync</h3>
      <p className="mt-2 text-sm text-ink-600">Use “Sync from PostgreSQL” to build it from recorded GPS movements and zone history.</p>
    </div> : null}

    {network.data?.ready ? <>
      <div className="flex flex-wrap items-end justify-between gap-3 rounded-panel border border-line bg-paper p-4">
        <div className="flex flex-wrap gap-3">
          <label className="space-y-1 text-xs text-ink-600"><span>Species</span><Select value={species} onChange={(event) => setSpecies(event.target.value)}><option value="">All species</option>{network.data.species.map((item) => <option value={item} key={item}>{item}</option>)}</Select></label>
          <label className="space-y-1 text-xs text-ink-600"><span>Crossings</span><Select value={days} onChange={(event) => setDays(event.target.value)}><option value="7">Last 7 days</option><option value="30">Last 30 days</option><option value="90">Last 90 days</option><option value="all">All recorded time</option></Select></label>
        </div>
        <div className="text-xs text-ink-600">{zones.length} zones · {corridors.length} connections · synced {label(network.data.synced_at)}{network.data.stale ? " · new GPS awaiting sync" : ""}</div>
      </div>
      <div className="grid gap-4 xl:grid-cols-[minmax(0,1.7fr)_minmax(300px,1fr)]">
        <div className="space-y-3">
          <div className="overflow-hidden rounded-panel border border-line bg-paper">
            <div className="flex flex-wrap items-center justify-between gap-3 border-b border-line px-4 py-3">
              <div>
                <h3 className="flex items-center gap-2 text-sm font-semibold"><GitBranch className="h-4 w-4" /> Zone connections</h3>
                <p className="mt-1 text-xs text-ink-600">Each link is an observed move between zones, not an exact trail.</p>
              </div>
              <div className="flex items-center gap-2">
                <div className="flex rounded-control border border-line bg-moss-100 p-0.5" aria-label="Connection view">
                  <button type="button" onClick={() => { setView("routes"); setHovered(null); }} aria-pressed={view === "routes"} className={`rounded px-3 py-1.5 text-xs font-medium ${view === "routes" ? "bg-paper text-forest-700 shadow-sm" : "text-ink-600"}`}>Connections</button>
                  <button type="button" onClick={() => { setView("diagram"); setHovered(null); }} aria-pressed={view === "diagram"} className={`rounded px-3 py-1.5 text-xs font-medium ${view === "diagram" ? "bg-paper text-forest-700 shadow-sm" : "text-ink-600"}`}>Diagram</button>
                </div>
                {selected ? <button type="button" onClick={() => setSelected(null)} className="rounded-control border border-line px-3 py-1.5 text-xs font-medium hover:bg-moss-100">Clear</button> : null}
              </div>
            </div>
            {view === "routes" ? <div className="p-4">
              <div className="mb-3 flex items-center justify-between text-xs text-ink-600"><span>Observed direction</span><span>Most crossings first</span></div>
              {rankedCorridors.length ? <div className="space-y-2">{rankedCorridors.map((edge) => {
                const key = `${edge.from_zone_id}|${edge.to_zone_id}`;
                const active = selectedKey === key;
                return <button key={key} type="button" onClick={() => setSelected({ kind: "corridor", from: edge.from_zone_id, to: edge.to_zone_id })} onMouseEnter={() => setHovered({ kind: "corridor", from: edge.from_zone_id, to: edge.to_zone_id })} onMouseLeave={() => setHovered(null)} onFocus={() => setHovered({ kind: "corridor", from: edge.from_zone_id, to: edge.to_zone_id })} onBlur={() => setHovered(null)} aria-pressed={active} className={`w-full rounded-control border p-3 text-left transition-colors ${active ? "border-forest-700 bg-moss-100" : "border-line hover:bg-moss-100"}`}>
                  <span className="flex flex-wrap items-center gap-2 text-sm font-medium">
                    <span className="min-w-0 flex-1 truncate">{byId.get(edge.from_zone_id)?.name}</span>
                    <ArrowRight className="h-3 w-3 shrink-0 stroke-[1.5] text-forest-700" />
                    <span className="min-w-0 flex-1 truncate text-right">{byId.get(edge.to_zone_id)?.name}</span>
                  </span>
                  <span className="mt-2 flex items-center gap-3">
                    <span className="h-1.5 min-w-0 flex-1 overflow-hidden rounded-full bg-moss-100"><span className="block h-full rounded-full bg-forest-700" style={{ width: `${Math.max(6, edge.crossings / maxCrossings * 100)}%` }} /></span>
                    <span className="shrink-0 text-xs tabular-nums text-ink-600">{edge.crossings} crossing{edge.crossings === 1 ? "" : "s"} · {edge.animals} animal{edge.animals === 1 ? "" : "s"}</span>
                  </span>
                </button>;
              })}</div> : <p className="py-8 text-center text-sm text-ink-600">No zone-to-zone movements in this filter.</p>}
              {zones.length ? <div className="mt-5 border-t border-line pt-4">
                <h4 className="text-xs font-semibold uppercase tracking-wide text-ink-400">Explore a zone</h4>
                <div className="mt-2 flex flex-wrap gap-2">{zones.map((zone) => <button key={zone.zone_id} type="button" onClick={() => setSelected({ kind: "zone", zone_id: zone.zone_id })} aria-pressed={selected?.kind === "zone" && selected.zone_id === zone.zone_id} className={`rounded-control border px-2.5 py-1.5 text-xs font-medium transition-colors ${selected?.kind === "zone" && selected.zone_id === zone.zone_id ? "border-forest-700 bg-moss-100" : "border-line hover:bg-moss-100"}`}>{zone.name}</button>)}</div>
              </div> : null}
            </div> : <div>
              <p className="px-4 pt-3 text-xs text-ink-600">Hover to trace a link. Select a link or zone to inspect it.</p>
              <div className="overflow-x-auto">
                <svg viewBox="0 0 1000 600" className="block min-w-[700px] w-full" aria-label="Interactive network diagram of zones and observed movements">
                  <defs><marker id="network-arrow" viewBox="0 0 8 8" refX="7" refY="4" markerWidth="3" markerHeight="3" orient="auto"><path d="M 1 1 L 7 4 L 1 7" fill="none" stroke="#547663" strokeWidth="1.1" strokeLinecap="round" strokeLinejoin="round" /></marker></defs>
                  <ellipse cx="500" cy="300" rx="335" ry="215" fill="none" stroke="#dce7dd" strokeDasharray="5 9" />
                  {corridors.map((edge) => {
                    const from = positions.get(edge.from_zone_id);
                    const to = positions.get(edge.to_zone_id);
                    if (!from || !to) return null;
                    const key = `${edge.from_zone_id}|${edge.to_zone_id}`;
                    const active = selectedKey === key;
                    const emphasized = focus?.kind === "corridor"
                      ? focus.from === edge.from_zone_id && focus.to === edge.to_zone_id
                      : focus?.kind === "zone"
                        ? focus.zone_id === selected?.zone_id && impactedCorridors.size
                          ? impactedCorridors.has(key)
                          : focus.zone_id === edge.from_zone_id || focus.zone_id === edge.to_zone_id
                        : false;
                    const muted = Boolean(focus && !emphasized);
                    const d = curve(from, to);
                    const choose = () => setSelected({ kind: "corridor", from: edge.from_zone_id, to: edge.to_zone_id });
                    return <g key={key}>
                      <path d={d} fill="none" stroke={active || emphasized ? "#1f4a33" : "#8aa696"} strokeWidth={active || emphasized ? 2.2 : 1.25} strokeOpacity={muted ? 0.12 : emphasized || active ? 0.95 : 0.48} markerEnd={muted ? undefined : "url(#network-arrow)"} className="pointer-events-none transition-opacity" />
                      <path d={d} fill="none" stroke="transparent" strokeWidth="18" className="cursor-pointer" role="button" tabIndex="0" aria-label={`${byId.get(edge.from_zone_id)?.name} to ${byId.get(edge.to_zone_id)?.name}, ${edge.crossings} crossings by ${edge.animals} animals`} onMouseEnter={() => setHovered({ kind: "corridor", from: edge.from_zone_id, to: edge.to_zone_id })} onMouseLeave={() => setHovered(null)} onFocus={() => setHovered({ kind: "corridor", from: edge.from_zone_id, to: edge.to_zone_id })} onBlur={() => setHovered(null)} onClick={choose} onKeyDown={(event) => { if (event.key === "Enter" || event.key === " ") { event.preventDefault(); choose(); } }}><title>{edge.crossings} crossings by {edge.animals} animals</title></path>
                    </g>;
                  })}
                  {zones.map((zone) => {
                    const point = positions.get(zone.zone_id);
                    if (!point) return null;
                    const active = selected?.kind === "zone" && selected.zone_id === zone.zone_id;
                    const related = !focusZones || focusZones.has(zone.zone_id) || (focus?.kind === "zone" && (focus.zone_id === selected?.zone_id && impactedZoneIds.has(zone.zone_id) || corridors.some((edge) => (edge.from_zone_id === focus.zone_id && edge.to_zone_id === zone.zone_id) || (edge.to_zone_id === focus.zone_id && edge.from_zone_id === zone.zone_id))));
                    const choose = () => setSelected({ kind: "zone", zone_id: zone.zone_id });
                    return <g key={zone.zone_id} role="button" tabIndex="0" className="cursor-pointer transition-opacity" opacity={related ? 1 : 0.28} aria-label={`Inspect ${zone.name}`} onMouseEnter={() => setHovered({ kind: "zone", zone_id: zone.zone_id })} onMouseLeave={() => setHovered(null)} onFocus={() => setHovered({ kind: "zone", zone_id: zone.zone_id })} onBlur={() => setHovered(null)} onClick={choose} onKeyDown={(event) => { if (event.key === "Enter" || event.key === " ") { event.preventDefault(); choose(); } }}>
                      <circle cx={point.x} cy={point.y} r={active ? 31 : 27} fill="#fbfcfa" stroke={active || impacted.has(zone.zone_id) ? "#1f4a33" : riskColor[zone.risk_level] ?? "#6d9b5f"} strokeWidth={active ? 5 : 3} />
                      <text x={point.x} y={point.y + 4} textAnchor="middle" fontSize="12" fontWeight="700" fill="#16201a">{zone.zone_id.slice(-3)}</text>
                      <text x={point.x} y={point.y + 48} textAnchor="middle" fontSize="14" fontWeight={active ? "700" : "500"} fill="#16201a">{zone.name.length > 20 ? `${zone.name.slice(0, 18)}…` : zone.name}</text>
                      <title>{zone.name} · {zone.risk_level} risk</title>
                    </g>;
                  })}
                </svg>
              </div>
              <div className="flex flex-wrap items-center gap-x-5 gap-y-2 border-t border-line px-4 py-3 text-xs text-ink-600">
                <span>Thin arrows show observed direction</span>
                <span>Selected links are highlighted</span>
              </div>
            </div>}
          </div>
        </div>
        <aside className="rounded-panel border border-line bg-paper p-4">
          {!selected ? <div><h3 className="font-display text-xl">Explore the network</h3><p className="mt-2 text-sm text-ink-600">Select a connection for contributing animals and alerts, or a zone to inspect historically connected habitats. Zone impact uses all recorded connections, independent of the filters above.</p></div> : null}
          {selected?.kind === "corridor" ? <div>
            <h3 className="font-display text-xl">{byId.get(selected.from)?.name} → {byId.get(selected.to)?.name}</h3>
            {detail.loading ? <p className="mt-3 text-sm text-ink-600">Loading connection details…</p> : detail.error ? <p className="mt-3 text-sm text-red-700">{detail.error.message}</p> : detail.data ? <>
              <p className="mt-2 text-sm text-ink-600">{detail.data.crossings} crossings by {detail.data.animals.length} animals in this filter.</p>
              <h4 className="mt-5 text-xs font-semibold uppercase tracking-wide text-ink-400">Contributing animals</h4>
              <div className="mt-2 space-y-2">{detail.data.animals.map((animal) => <div key={animal.animal_id} className="rounded-control border border-line p-2 text-sm"><Link className="font-medium text-forest-700 underline" to={`/animals/${animal.animal_id}`}>{animal.animal_code}</Link> · {animal.species} <span className="float-right tabular">{animal.crossings} crossings</span></div>)}</div>
              <h4 className="mt-5 text-xs font-semibold uppercase tracking-wide text-ink-400">Related alerts</h4>
              {detail.data.alerts.length ? <div className="mt-2 space-y-2">{detail.data.alerts.map((alert) => <div key={alert.alert_id} className="rounded-control border border-line p-2 text-xs"><strong>{alert.severity}</strong> · {alert.message}<div className="mt-1 text-ink-400">{label(alert.created_at)}</div></div>)}</div> : <p className="mt-2 text-sm text-ink-600">No related alerts in this filter.</p>}
            </> : null}
          </div> : null}
          {selected?.kind === "zone" ? <div>
            <h3 className="font-display text-xl">{byId.get(selected.zone_id)?.name}</h3>
            <div className="mt-2 flex items-center gap-2 text-sm text-ink-600"><ShieldAlert className="h-4 w-4" /> Historical habitat connections</div>
            {detail.loading ? <p className="mt-3 text-sm text-ink-600">Tracing connected zones…</p> : detail.error ? <p className="mt-3 text-sm text-red-700">{detail.error.message}</p> : detail.data ? <>
              <p className="mt-3 text-xs text-ink-600">{detail.data.basis}</p>
              <h4 className="mt-5 text-xs font-semibold uppercase tracking-wide text-ink-400">Observed corridors connected to this zone</h4>
              {detail.data.corridors?.length ? <div className="mt-2 space-y-2">{detail.data.corridors.map((edge) => <div key={`${edge.from_zone_id}|${edge.to_zone_id}`} className="rounded-control border border-line p-2.5 text-sm">
                <div className="flex items-center gap-1 font-medium"><span className="min-w-0 truncate">{byId.get(edge.from_zone_id)?.name ?? edge.from_zone_id}</span><ArrowRight className="h-3 w-3 shrink-0 stroke-[1.5] text-forest-700" /><span className="min-w-0 truncate">{byId.get(edge.to_zone_id)?.name ?? edge.to_zone_id}</span></div>
                <div className="mt-1 text-xs text-ink-600">{edge.hops} step{edge.hops === 1 ? "" : "s"} from selected zone · {edge.crossings} crossings · {edge.animals} animals</div>
              </div>)}</div> : <p className="mt-2 text-sm text-ink-600">No observed corridors connect to this zone.</p>}
              <h4 className="mt-5 text-xs font-semibold uppercase tracking-wide text-ink-400">Connected zones · up to 3 connections</h4>
              {detail.data.reachable_zones.length ? <div className="mt-2 space-y-2">{detail.data.reachable_zones.map((item) => <div key={item.zone_id} className="rounded-control border border-line p-2 text-sm"><strong>{byId.get(item.zone_id)?.name ?? item.zone_id}</strong><div className="text-xs text-ink-600">{item.hops} step{item.hops === 1 ? "" : "s"} · {item.path.map((id) => byId.get(id)?.name ?? id).join(" ↔ ")}</div></div>)}</div> : <p className="mt-2 text-sm text-ink-600">No connected corridor has been observed.</p>}
              <h4 className="mt-5 text-xs font-semibold uppercase tracking-wide text-ink-400">Animals observed on connected corridors</h4>
              <p className="mt-2 text-sm">{detail.data.animals.length} animals</p>
              <div className="mt-2 flex flex-wrap gap-2">{detail.data.animals.map((animal) => <Link key={animal.animal_id} to={`/animals/${animal.animal_id}`} className="rounded-control border border-line px-2 py-1 font-mono text-xs hover:bg-moss-100">{animal.animal_code} · {animal.crossings} crossing{animal.crossings === 1 ? "" : "s"}</Link>)}</div>
              <h4 className="mt-5 text-xs font-semibold uppercase tracking-wide text-ink-400">Recent related alerts</h4>
              {detail.data.alerts.length ? <div className="mt-2 space-y-2">{detail.data.alerts.slice(0, 5).map((alert) => <div key={alert.alert_id} className="rounded-control border border-line p-2 text-xs">{alert.message}</div>)}</div> : <p className="mt-2 text-sm text-ink-600">No related alerts.</p>}
            </> : null}
          </div> : null}
        </aside>
      </div>
    </> : null}
  </div>;
};
