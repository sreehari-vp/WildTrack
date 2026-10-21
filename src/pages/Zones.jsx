import { useEffect, useMemo, useState } from "react";
import { RiskBadge } from "../components/animals/StatusBadge";
import { ForestMap } from "../components/map/ForestMap";
import { Select } from "../components/common/Select";
import { ZoneList } from "../components/zones/ZoneList";
import { useAlerts } from "../hooks/useAlerts";
import { useAnimals } from "../hooks/useAnimals";
import { useAsyncData } from "../hooks/useAsyncData";
import { useZoneAnimals, useZones, useZoneTransitions, useBoundary } from "../hooks/useZones";
import { researchService } from "../services/researchService";
import { formatTime } from "../utils/format";
import { riskMeta, zoneLabels } from "../utils/risk";
import { DataState } from "./PageState";

const Zones = () => {
  const [selectedZoneId, setSelectedZoneId] = useState();
  const [typeFilter, setTypeFilter] = useState("all");
  const [riskFilter, setRiskFilter] = useState("all");
  const zones = useZones();
  const animals = useAnimals();
  const alerts = useAlerts();
  const boundary = useBoundary();
  const areas = useAsyncData(() => researchService.getAreas(), []);
  const filteredZones = useMemo(() => (zones.data ?? []).filter((zone) =>
    (typeFilter === "all" || zone.type === typeFilter)
    && (riskFilter === "all" || zone.risk === riskFilter)
  ), [zones.data, typeFilter, riskFilter]);
  const selectedZone = filteredZones.find((zone) => zone.id === selectedZoneId) ?? filteredZones[0];
  const selectedZoneAlerts = alerts.data?.filter((alert) => alert.zoneId === selectedZone?.id) ?? [];
  const zoneAnimals = useZoneAnimals(selectedZone?.id);
  const zoneTransitions = useZoneTransitions(selectedZone?.id);
  const loading = zones.loading || boundary.loading || areas.loading;
  const error = zones.error || boundary.error || areas.error;

  useEffect(() => {
    if (!filteredZones.some((zone) => zone.id === selectedZoneId)) {
      setSelectedZoneId(filteredZones[0]?.id);
    }
  }, [filteredZones, selectedZoneId]);

  if (loading || error || !zones.data || !boundary.data || !areas.data
  ) {
    return <div className="p-6"><DataState loading={loading} error={error} onRetry={() => {
      zones.retry(); animals.retry(); alerts.retry(); boundary.retry(); areas.retry();
      zoneAnimals.retry(); zoneTransitions.retry();
    }} /></div>;
  }

  const regionFeatures = areas.data.features.filter((feature) => feature.properties?.kind === "region");
  const regionCount = regionFeatures.length;
  const classCount = new Set(zones.data.map((zone) => zone.type)).size;

  return <div className="space-y-5 p-6">
    <header className="flex flex-wrap items-end justify-between gap-4">
      <div>
        <p className="text-xs font-semibold uppercase tracking-[.16em] text-forest-700">Ooty operational geography</p>
        <h1 className="font-display text-3xl text-ink-900">Land Cover &amp; Zones</h1>
        <p className="mt-1 max-w-3xl text-sm text-ink-600">Explore ESA land-cover zones within each forest region, inspect animal activity, and manage operational zones on the map.</p>
      </div>
      <div className="flex flex-wrap gap-2 text-xs">
        <span className="rounded-control border border-line bg-paper px-3 py-2">{regionCount} regions</span>
        <span className="rounded-control border border-line bg-paper px-3 py-2">{zones.data.length} operational zones</span>
        <span className="rounded-control border border-line bg-paper px-3 py-2">{classCount} land-cover classes</span>
      </div>
    </header>

    <section className="overflow-hidden rounded-panel border border-line bg-paper shadow-sm" aria-label="Ooty regions and operational zones map">
      <div className="flex flex-wrap items-center justify-between gap-3 border-b border-line p-3">
        <div className="text-sm font-medium text-ink-900">Ooty regions and zones</div>
        <div className="flex flex-wrap items-center gap-3 text-xs text-ink-600">
          <span className="flex items-center gap-1.5"><i className="h-3 w-5 rounded-sm bg-[#327a52]/70" /> Satellite land cover</span>
          <span className="flex items-center gap-1.5"><i className="h-0.5 w-5 bg-[#214b35]" /> Study region boundary</span>
          <span>Outlined overlay: operational status</span>
        </div>
      </div>
      <ForestMap
        animals={animals.data ?? []}
        devices={[]}
        zones={zones.data}
        boundary={boundary.data}
        studyRegions={regionFeatures}
        alerts={alerts.data ?? []}
        hideAlertSummary
        scrollZoomEnabled={false}
        selectedZoneId={selectedZone?.id}
        onZonesChanged={zones.refresh}
        className="h-[min(68vh,680px)] min-h-[480px]"
      />
    </section>

    <div className="flex flex-wrap items-center justify-between gap-3">
      <div>
        <h2 className="font-display text-2xl text-ink-900">Zone operations</h2>
        <p className="mt-1 text-sm text-ink-600">Select a row to inspect current animals and recent boundary transitions.</p>
      </div>
      <div className="flex flex-wrap gap-2">
        <Select aria-label="Filter zone type" value={typeFilter} onChange={(event) => setTypeFilter(event.target.value)}>
          <option value="all">All land-cover types</option>
          {Object.entries(zoneLabels).map(([value, label]) => <option key={value} value={value}>{label}</option>)}
        </Select>
        <Select aria-label="Filter zone status" value={riskFilter} onChange={(event) => setRiskFilter(event.target.value)}>
          <option value="all">All statuses</option>
          {Object.entries(riskMeta).map(([value, meta]) => <option key={value} value={value}>{meta.label}</option>)}
        </Select>
      </div>
    </div>

    {selectedZone ? <section className="rounded-panel border border-line bg-paper p-4">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <div className="text-xs text-ink-400">{zoneLabels[selectedZone.type]} · {selectedZone.regionName ?? "Unassigned region"}</div>
          <h3 className="font-display text-xl text-ink-900">{selectedZone.name}</h3>
          <p className="mt-1 max-w-3xl text-sm text-ink-600">{selectedZone.description}</p>
        </div>
        <RiskBadge risk={selectedZone.risk} />
      </div>
      <p className="mt-3 rounded-control bg-moss-100 px-3 py-2 text-xs text-ink-600">Calm, OK, Watch, and Danger are illustrative scenario-monitoring classes derived from land cover. They are not official hazard ratings.</p>
      <div className="mt-4 grid gap-4 md:grid-cols-2 xl:grid-cols-3">
        <div>
          <div className="text-xs text-ink-400">Current animals inside</div>
          <div className="mt-2 flex flex-wrap gap-2">
            {zoneAnimals.loading ? <span className="text-sm text-ink-600">Loading zone activity…</span> : zoneAnimals.error ? <button className="text-sm text-risk-high underline" onClick={zoneAnimals.retry}>Could not load · Retry</button> : zoneAnimals.data?.length ? zoneAnimals.data.map((animal) => <span key={animal.id} className="rounded-control border border-line bg-moss-100 px-2 py-1 font-mono text-xs tabular">{animal.id}</span>) : <span className="text-sm text-ink-600">No tracked animals currently inside.</span>}
          </div>
        </div>
        <div>
          <div className="text-xs text-ink-400">Recent zone entries and exits</div>
          <div className="mt-2 space-y-2">
            {zoneTransitions.loading ? <span className="text-sm text-ink-600">Loading recent transitions…</span> : zoneTransitions.error ? <button className="text-sm text-risk-high underline" onClick={zoneTransitions.retry}>Could not load · Retry</button> : zoneTransitions.data?.length ? zoneTransitions.data.slice(0, 4).map((transition, index) => <div key={`${transition.transitioned_at}-${index}`} className="flex items-center justify-between gap-3 text-sm">
              <span className="truncate font-mono text-xs tabular">{transition.animal_code}</span>
              <span className="truncate text-ink-600">{transition.from_zone?.name ?? "Outside monitored zones"} → {transition.to_zone?.name ?? "Outside monitored zones"}</span>
              <span className="shrink-0 font-mono text-xs tabular text-ink-400">{formatTime(transition.transitioned_at)}</span>
            </div>) : <div className="text-sm text-ink-600">No recent transitions.</div>}
          </div>
        </div>
        <div>
          <div className="text-xs text-ink-400">Recent alerts</div>
          <div className="mt-2 space-y-2">
            {selectedZoneAlerts.length ? selectedZoneAlerts.slice(0, 4).map((alert) => <div key={alert.id} className="flex items-center justify-between gap-3 text-sm">
              <span className="truncate text-ink-700">{alert.title}</span>
              <span className="shrink-0 text-xs text-ink-600">{alert.severity} · {alert.status}</span>
            </div>) : <div className="text-sm text-ink-600">No alerts for this zone.</div>}
          </div>
        </div>
      </div>
    </section> : null}

    <ZoneList zones={filteredZones} animals={animals.data ?? []} alerts={alerts.data ?? []} selectedZoneId={selectedZone?.id} onSelectZone={(zone) => setSelectedZoneId(zone.id)} />
  </div>;
};

export { Zones };
