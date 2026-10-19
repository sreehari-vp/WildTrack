import { Link } from "react-router-dom";
import { DataState } from "./PageState";
import { useAlerts } from "../hooks/useAlerts";
import { useAnimals } from "../hooks/useAnimals";
import { useAsyncData } from "../hooks/useAsyncData";
import { useZones } from "../hooks/useZones";
import { monitoringService } from "../services/monitoringService";
import { researchService } from "../services/researchService";
import { riskMeta } from "../utils/risk";

const Overview = () => {
  const areas = useAsyncData(() => researchService.getAreas(true), []);
  const animals = useAnimals();
  const zones = useZones();
  const alerts = useAlerts();
  const simulation = useAsyncData(monitoringService.getSimulationStatus, [], { intervalMs: 5000 });
  const loading = areas.loading || animals.loading || zones.loading || alerts.loading || simulation.loading;
  const error = areas.error || animals.error || zones.error || alerts.error || simulation.error;

  if (loading || error || !areas.data || !animals.data || !zones.data || !alerts.data || !simulation.data) {
    return <div className="p-6"><DataState loading={loading} error={error} onRetry={() => {
      areas.retry(); animals.retry(); zones.retry(); alerts.retry(); simulation.retry();
    }} /></div>;
  }

  const regions = areas.data.features.filter((feature) => feature.properties?.kind === "region");
  const landCoverZones = areas.data.features.filter((feature) => feature.properties?.kind === "land_cover");
  const openAlerts = alerts.data.filter((alert) => alert.status !== "resolved");
  const regionCards = regions.map((region) => {
    const code = region.properties.code;
    const regionZones = zones.data.filter((zone) => zone.regionCode === code);
    const animalsInside = animals.data.filter((animal) => regionZones.some((zone) => zone.id === animal.currentZoneId)).length;
    const dangerZones = regionZones.filter((zone) => zone.risk === "high" || zone.risk === "critical").length;
    return { ...region.properties, regionZones, animalsInside, dangerZones };
  });
  const running = Boolean(simulation.data.running);

  return <div className="space-y-6 p-6">
    <header className="flex flex-wrap items-end justify-between gap-4">
      <div>
        <p className="text-xs font-semibold uppercase tracking-[.16em] text-forest-700">Nilgiri reserve · Ooty study area</p>
        <h1 className="font-display text-3xl text-ink-900">Wildlife overview</h1>
        <p className="mt-1 max-w-3xl text-sm text-ink-600">A current summary of the eight forest analysis regions, sourced land cover, tracked scenario animals, and operational alerts.</p>
      </div>
      <Link to="/" className="rounded-control border border-line bg-paper px-4 py-2 text-sm font-medium text-forest-700 hover:bg-moss-100">Open Ooty map</Link>
    </header>

    <section className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4" aria-label="Reserve summary">
      {[
        ["Forest regions", regions.length, "Source-derived analysis extents"],
        ["Land-cover zones", landCoverZones.length, "ESA WorldCover · 2021 · 10 m"],
        ["Scenario animals", animals.data.length, "Synthetic trackers · not live collars"],
        ["Open alerts", openAlerts.length, running ? "Simulation is running" : "Simulation stopped"]
      ].map(([label, value, note]) => <div key={label} className="rounded-panel border border-line bg-paper p-4 shadow-sm">
        <div className="text-xs font-semibold uppercase tracking-wide text-ink-400">{label}</div>
        <div className="mt-2 font-display text-3xl text-ink-900">{value}</div>
        <div className="mt-1 text-xs text-ink-600">{note}</div>
      </div>)}
    </section>

    <section className="rounded-panel border border-line bg-paper p-4 shadow-sm">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h2 className="font-display text-xl text-ink-900">Region coverage</h2>
          <p className="mt-1 text-sm text-ink-600">Animals are assigned to regions through their latest point and the operational zone that contains it.</p>
        </div>
        <div className="flex gap-2 text-xs">
          <span className={`rounded-control px-3 py-1.5 ${running ? "bg-moss-100 text-forest-700" : "bg-paper text-ink-600 border border-line"}`}>{running ? "Simulation running" : "Simulation stopped"}</span>
          <span className="rounded-control border border-line bg-paper px-3 py-1.5">{simulation.data.completed_routes}/{simulation.data.total_routes} routes complete</span>
        </div>
      </div>
      <div className="mt-4 grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
        {regionCards.map((region) => <article key={region.code} className="rounded-panel border border-line bg-moss-100/50 p-4">
          <h3 className="font-medium text-ink-900">{region.name}</h3>
          <p className="mt-1 text-xs text-ink-600">{Number(region.area_sq_km).toFixed(1)} km² · {region.regionZones.length} land-cover zones</p>
          <div className="mt-3 flex items-center justify-between text-sm">
            <span className="text-ink-600">Animals inside</span>
            <span className="font-mono tabular text-ink-900">{region.animalsInside}</span>
          </div>
          <div className="mt-1 flex items-center justify-between text-xs">
            <span className="text-ink-600">Danger-class scenario zones</span>
            <span className={`font-medium ${riskMeta.high.className}`}>{region.dangerZones}</span>
          </div>
        </article>)}
      </div>
    </section>

    <section className="grid gap-4 lg:grid-cols-2">
      <div className="rounded-panel border border-line bg-paper p-4">
        <h2 className="font-display text-xl text-ink-900">Land-cover classes</h2>
        <p className="mt-1 text-sm text-ink-600">Mapped classes describe satellite land cover. Scenario status is illustrative, not an official hazard rating.</p>
        <div className="mt-4 flex flex-wrap gap-2">
          {[...new Set(landCoverZones.map((feature) => feature.properties.zone_type))].sort().map((type) => <span key={type} className="rounded-control border border-line bg-moss-100 px-3 py-2 text-xs text-ink-700">{type.replaceAll("_", " ")}</span>)}
        </div>
        <Link to="/zones" className="mt-4 inline-block text-sm font-medium text-forest-700 underline">Explore zones and region boundaries</Link>
      </div>
      <div className="rounded-panel border border-line bg-paper p-4">
        <h2 className="font-display text-xl text-ink-900">Data sources</h2>
        <div className="mt-3 space-y-3 text-sm text-ink-600">
          <p><strong className="text-ink-900">PostgreSQL/PostGIS</strong> stores canonical regions, operational zones, animal records, observations, and alerts.</p>
          <p><strong className="text-ink-900">ESA WorldCover 2021</strong> supplies the mapped land-cover classes.</p>
          <p><strong className="text-ink-900">Wildlife records</strong> are sourced historical sightings. The 75 current tracker routes are a software simulation, not actual collar telemetry.</p>
        </div>
      </div>
    </section>
  </div>;
};

export { Overview };
