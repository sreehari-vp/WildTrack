import maplibregl from "maplibre-gl";
import { useEffect, useMemo, useRef, useState } from "react";
import { useSearchParams } from "react-router-dom";
import { useAsyncData } from "../hooks/useAsyncData";
import { researchService } from "../services/researchService";
import { animalService } from "../services/animalService";
import { monitoringService } from "../services/monitoringService";
import { apiUrl } from "../services/apiClient";
import { riskMeta } from "../utils/risk";

const emptyCollection = { type: "FeatureCollection", features: [] };
const landCoverColor = ["match", ["get", "zone_type"],
  "tree_cover", "#3d7450", "grassland", "#b6a963", "surface_water", "#5a9db2",
  "built_up", "#b87959", "cultivated_land", "#bea063", "bare_or_sparse_cover", "#967663", "#839477"];

const extendGeometry = (bounds, coordinates) => {
  if (typeof coordinates?.[0] === "number") bounds.extend(coordinates);
  else coordinates?.forEach((part) => extendGeometry(bounds, part));
};

const readableDate = (value) => {
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? value : date.toLocaleDateString();
};

export const FieldRecords = ({ defaultLandCover = false, title = "Ooty Forest Map", description = "Green dots are dated public mammal sightings. Coloured dots are synthetic trackers; their positions and movement are simulated." }) => {
  const areas = useAsyncData(() => researchService.getAreas(false), []);
  const records = useAsyncData(researchService.getOccurrences, []);
  const simulated = useAsyncData(animalService.getAnimals, []);
  const simulation = useAsyncData(monitoringService.getSimulationStatus, [], { intervalMs: 1000 });
  const [simulationBusy, setSimulationBusy] = useState(false);
  const [simulationError, setSimulationError] = useState(null);
  const [simulationVisible, setSimulationVisible] = useState(true);
  const [simulationSpecies, setSimulationSpecies] = useState("all");
  const [landCoverVisible, setLandCoverVisible] = useState(defaultLandCover);
  const [landCover, setLandCover] = useState({ data: null, loading: false, error: null });
  const [landCoverRetry, setLandCoverRetry] = useState(0);
  const landCoverRequestedRef = useRef(false);
  const [regionCode, setRegionCode] = useState("all");
  const [speciesSearch, setSpeciesSearch] = useState("");
  const [className, setClassName] = useState("all");
  const [year, setYear] = useState("all");
  const [insideOnly, setInsideOnly] = useState(false);
  const [selectedId, setSelectedId] = useState(null);
  const [mapReady, setMapReady] = useState(false);
  const [searchParams] = useSearchParams();
  const containerRef = useRef(null);
  const mapRef = useRef(null);
  const popupRef = useRef(null);
  const regionNameByCodeRef = useRef(new Map());
  const recordsByIdRef = useRef(new Map());
  const animalsByIdRef = useRef(new Map());
  const focusedSearchRef = useRef("");

  useEffect(() => {
    if (!landCoverVisible || landCoverRequestedRef.current) return;
    landCoverRequestedRef.current = true;
    setLandCover({ data: null, loading: true, error: null });
    researchService.getLandCoverAreas().then((data) => {
      setLandCover({ data, loading: false, error: null });
    }).catch((error) => {
      setLandCover({ data: null, loading: false, error });
    });
  }, [landCoverVisible, landCoverRetry]);

  const regions = useMemo(() => areas.data?.features?.filter((feature) => feature.properties?.kind === "region") ?? [], [areas.data]);
  const regionNameByCode = useMemo(() => new Map(regions.map((region) => [region.properties.code, region.properties.name])), [regions]);
  regionNameByCodeRef.current = regionNameByCode;
  const occurrences = useMemo(() => records.data?.occurrences ?? [], [records.data]);
  const simulationAnimals = useMemo(() => {
    const metadata = new Map((simulated.data ?? []).map((animal) => [animal.id, animal]));
    return Object.entries(simulation.data?.animals ?? {})
      .filter(([id]) => id.startsWith("SIM-V2-"))
      .map(([id, live]) => ({
        ...(metadata.get(id) ?? { id, name: id, species: "Wildlife", coordinates: [null, null] }),
        coordinates: live.coordinates ?? metadata.get(id)?.coordinates ?? [null, null]
      }));
  }, [simulated.data, simulation.data?.animals]);
  const simulationSpeciesOptions = useMemo(() => [...new Set(simulationAnimals.map((animal) => animal.species))].sort(), [simulationAnimals]);
  const visibleSimulationAnimals = useMemo(() => simulationAnimals.filter((animal) =>
    simulationVisible && (simulationSpecies === "all" || animal.species === simulationSpecies)
    && animal.coordinates.every(Number.isFinite)
  ), [simulationAnimals, simulationVisible, simulationSpecies]);
  animalsByIdRef.current = new Map(simulationAnimals.map((animal) => [animal.id, animal]));
  const simulationStatus = simulation.data;
  const simulationStatusRef = useRef(simulationStatus);
  simulationStatusRef.current = simulationStatus;
  const routeCount = simulationStatus?.total_routes ?? 0;
  const completedRoutes = simulationStatus?.completed_routes ?? 0;
  const classes = useMemo(() => [...new Set(occurrences.map((item) => item.taxonomic_class).filter(Boolean))].sort(), [occurrences]);
  const years = useMemo(() => [...new Set(occurrences.map((item) => item.source_observed_at.slice(0, 4)))].sort().reverse(), [occurrences]);
  const filtered = useMemo(() => occurrences.filter((item) => {
    const memberships = regionCode === "all" ? item.regions : item.regions.filter((region) => region.code === regionCode);
    return memberships.length > 0
      && item.species.toLowerCase().includes(speciesSearch.trim().toLowerCase())
      && (className === "all" || item.taxonomic_class === className)
      && (year === "all" || item.source_observed_at.startsWith(year))
      && (!insideOnly || memberships.some((region) => !region.uncertainty_crosses_boundary));
  }), [occurrences, regionCode, speciesSearch, className, year, insideOnly]);
  recordsByIdRef.current = new Map(occurrences.map((item) => [String(item.id), item]));
  const distinctSpecies = new Set(occurrences.map((item) => item.species)).size;
  const areaFeatures = useMemo(() => landCoverVisible && landCover.data
    ? [...regions, ...landCover.data.features]
    : regions, [landCoverVisible, landCover.data, regions]);
  const clearFilters = () => { setRegionCode("all"); setSpeciesSearch(""); setClassName("all"); setYear("all"); setInsideOnly(false); setSimulationSpecies("all"); };
  useEffect(() => {
    if (!mapReady || !mapRef.current) return;
    const animalId = searchParams.get("animal");
    const zoneId = searchParams.get("zone");
    const focusKey = `${animalId ?? ""}|${zoneId ?? ""}`;
    if (focusKey === focusedSearchRef.current || (!animalId && !zoneId)) return;
    if (animalId) {
      const animal = simulationAnimals.find((item) => item.id === animalId);
      if (!animal?.coordinates?.every(Number.isFinite)) return;
      mapRef.current.flyTo({ center: animal.coordinates, zoom: Math.max(mapRef.current.getZoom(), 13), duration: 500 });
      focusedSearchRef.current = focusKey;
      return;
    }
    const area = areaFeatures.find((feature) => feature.id === `land-cover:${zoneId}`
      || feature.properties?.code === zoneId || feature.properties?.zone_id === zoneId);
    if (!area?.geometry) return;
    const bounds = new maplibregl.LngLatBounds();
    extendGeometry(bounds, area.geometry.coordinates);
    if (!bounds.isEmpty()) mapRef.current.fitBounds(bounds, { padding: 60, maxZoom: 13, duration: 500 });
    focusedSearchRef.current = focusKey;
  }, [mapReady, searchParams, simulationAnimals, areaFeatures]);
  useEffect(() => {
    const stopOnRefreshOrClose = () => {
      if (!simulationStatusRef.current?.running || !navigator.sendBeacon) return;
      navigator.sendBeacon(apiUrl("/simulation/stop"), new Blob([], { type: "text/plain" }));
    };
    window.addEventListener("pagehide", stopOnRefreshOrClose);
    return () => window.removeEventListener("pagehide", stopOnRefreshOrClose);
  }, []);

  const toggleSimulation = async () => {
    if (simulationBusy) return;
    setSimulationBusy(true);
    setSimulationError(null);
    try {
      if (simulation.data?.running) await monitoringService.stopSimulation();
      else await monitoringService.startSimulation();
      await simulation.refresh();
    } catch (error) {
      setSimulationError(error.message);
    } finally {
      setSimulationBusy(false);
    }
  };

  useEffect(() => {
    if (!containerRef.current || mapRef.current) return;
    const map = new maplibregl.Map({
      container: containerRef.current, center: [76.7, 11.4], zoom: 10,
      attributionControl: { compact: true },
      style: { version: 8, sources: {
        osm: { type: "raster", tiles: ["https://tile.openstreetmap.org/{z}/{x}/{y}.png"], tileSize: 256, attribution: "© OpenStreetMap contributors" },
        areas: { type: "geojson", data: emptyCollection },
        records: { type: "geojson", data: emptyCollection },
        simulated: { type: "geojson", data: emptyCollection }
      }, layers: [{ id: "osm", type: "raster", source: "osm" }] }
    });
    mapRef.current = map;
    map.scrollZoom.disable();
    popupRef.current = new maplibregl.Popup({ closeButton: false, closeOnClick: false, offset: 10 });
    map.addControl(new maplibregl.NavigationControl({ showCompass: false }), "bottom-right");
    map.on("load", () => {
      map.addLayer({ id: "region-fill", type: "fill", source: "areas", filter: ["==", ["get", "kind"], "region"], paint: { "fill-color": "#53745d", "fill-opacity": 0.08 } });
      map.addLayer({ id: "land-cover-fill", type: "fill", source: "areas", filter: ["==", ["get", "kind"], "land_cover"], paint: { "fill-color": landCoverColor, "fill-opacity": 0.48 } });
      map.addLayer({ id: "region-casing", type: "line", source: "areas", filter: ["==", ["get", "kind"], "region"], paint: { "line-color": "#f7f6ef", "line-width": 6, "line-opacity": 0.96 } });
      map.addLayer({ id: "region-line", type: "line", source: "areas", filter: ["==", ["get", "kind"], "region"], paint: { "line-color": "#214b35", "line-width": 3.5, "line-opacity": 0.98 } });
      map.addLayer({ id: "land-cover-outline", type: "line", source: "areas", filter: ["==", ["get", "kind"], "land_cover"], paint: { "line-color": "#425747", "line-width": 0.65, "line-opacity": 0.62 } });
      map.addLayer({ id: "record-dots", type: "circle", source: "records", paint: { "circle-radius": ["interpolate", ["linear"], ["zoom"], 8, 2.3, 13, 3.4, 16, 4.2], "circle-color": "#22573b", "circle-stroke-color": "#fff8e6", "circle-stroke-width": 1 } });
      map.addLayer({ id: "simulated-dots", type: "circle", source: "simulated", paint: {
        "circle-radius": ["interpolate", ["linear"], ["zoom"], 8, 2.5, 13, 4, 16, 5],
        "circle-color": ["match", ["get", "species"], "Elephas maximus", "#3b78a3", "Panthera tigris", "#c45f31", "Nilgiritragus hylocrius", "#8564a5", "#d49b36"],
        "circle-stroke-color": "#102e25", "circle-stroke-width": 0.8
      } });
      map.addLayer({ id: "selected-record", type: "circle", source: "records", filter: ["==", ["get", "record_id"], ""], paint: { "circle-radius": 7, "circle-color": "#123b2b", "circle-stroke-color": "#eacb74", "circle-stroke-width": 2.5 } });
      setMapReady(true);
    });
    map.on("click", "record-dots", (event) => {
      const id = event.features?.[0]?.properties?.record_id;
      if (id != null) setSelectedId(String(id));
    });
    map.on("click", "simulated-dots", (event) => {
      const coordinates = event.features?.[0]?.geometry?.coordinates;
      if (Array.isArray(coordinates)) {
        setSelectedId(null);
        map.flyTo({ center: coordinates, zoom: Math.max(map.getZoom(), 13), duration: 450 });
      }
    });
    for (const layer of ["region-fill", "land-cover-fill"]) {
      map.on("click", layer, (event) => {
        if (map.queryRenderedFeatures(event.point, { layers: ["record-dots", "simulated-dots"] }).length) return;
        const feature = event.features?.[0];
        if (feature?.geometry) {
          const bounds = geometryBounds(feature.geometry);
          if (!bounds.isEmpty()) map.fitBounds(bounds, { padding: 60, maxZoom: 13, duration: 450 });
          setSelectedId(null);
        }
      });
    }
    map.on("mousemove", "record-dots", (event) => {
      map.getCanvas().style.cursor = "pointer";
      const id = String(event.features?.[0]?.properties?.record_id ?? "");
      const item = recordsByIdRef.current.get(id);
      if (!item) return;
      const content = document.createElement("div");
      content.textContent = `${item.species} · ${readableDate(item.source_observed_at)}`;
      popupRef.current?.setLngLat(event.lngLat).setDOMContent(content).addTo(map);
    });
    map.on("mouseleave", "record-dots", () => { map.getCanvas().style.cursor = ""; popupRef.current?.remove(); });
    map.on("mousemove", "simulated-dots", (event) => {
      map.getCanvas().style.cursor = "pointer";
      const id = String(event.features?.[0]?.properties?.animal_id ?? "");
      const animal = animalsByIdRef.current.get(id);
      if (!animal) return;
      const content = document.createElement("div");
      content.textContent = `${animal.name} · simulated movement`;
      popupRef.current?.setLngLat(event.lngLat).setDOMContent(content).addTo(map);
    });
    map.on("mouseleave", "simulated-dots", () => { map.getCanvas().style.cursor = ""; popupRef.current?.remove(); });
    for (const layer of ["region-fill", "land-cover-fill"]) {
      map.on("mousemove", layer, (event) => {
        const feature = event.features?.[0];
        if (!feature) return;
        map.getCanvas().style.cursor = "pointer";
        const props = feature.properties ?? {};
        const card = document.createElement("div");
        card.className = "grid gap-1 text-xs leading-snug";
        const title = document.createElement("strong");
        title.className = "text-sm";
        title.textContent = props.name ?? "Ooty forest feature";
        card.appendChild(title);
        const addLine = (label, value) => {
          if (!value) return;
          const line = document.createElement("span");
          line.textContent = `${label}: ${value}`;
          card.appendChild(line);
        };
        if (props.kind === "land_cover") {
          addLine("Land cover", String(props.zone_type ?? "").replaceAll("_", " "));
          addLine("Region", regionNameByCodeRef.current.get(props.region_code));
          addLine("Area", `${Number(props.area_sq_km).toFixed(2)} km²`);
          addLine("Source", "ESA WorldCover 2021 · 10 m");
          addLine("Scenario status", riskMeta[props.risk_level]?.label ?? "Unrated");
          addLine("Status basis", "Land-cover scenario only; not an official hazard assessment");
        } else {
          addLine("Forest area", props.boundary_type);
          addLine("Area", `${Number(props.area_sq_km).toFixed(2)} km²`);
          addLine("Source", props.source_name ?? props.data_source);
          addLine("Boundary status", props.legal_status);
        }
        popupRef.current?.setLngLat(event.lngLat).setDOMContent(card).addTo(map);
      });
      map.on("mouseleave", layer, () => { map.getCanvas().style.cursor = ""; popupRef.current?.remove(); });
    }
    return () => { popupRef.current?.remove(); map.remove(); mapRef.current = null; setMapReady(false); };
  }, []);

  useEffect(() => {
    const map = mapRef.current;
    if (!mapReady || !map) return;
    map.getSource("areas")?.setData({ type: "FeatureCollection", features: areaFeatures });
  }, [mapReady, areaFeatures]);
  useEffect(() => {
    const map = mapRef.current;
    if (!mapReady || !map || !regions.length || regionCode !== "all") return;
    const bounds = new maplibregl.LngLatBounds();
    regions.forEach((region) => extendGeometry(bounds, region.geometry.coordinates));
    if (!bounds.isEmpty()) map.fitBounds(bounds, { padding: 48, maxZoom: 12, duration: 0 });
  }, [mapReady, regions, regionCode]);
  useEffect(() => {
    const map = mapRef.current;
    if (!mapReady || !map) return;
    map.getSource("records")?.setData({ type: "FeatureCollection", features: filtered.map((item) => ({
      type: "Feature", properties: { record_id: String(item.id) },
      geometry: { type: "Point", coordinates: [item.longitude, item.latitude] }
    })) });
  }, [mapReady, filtered]);
  useEffect(() => {
    const map = mapRef.current;
    if (!mapReady || !map) return;
    map.setFilter("selected-record", ["==", ["get", "record_id"], selectedId ?? ""]);
  }, [mapReady, selectedId]);
  useEffect(() => {
    const map = mapRef.current;
    if (!mapReady || !map) return;
    map.getSource("simulated")?.setData({ type: "FeatureCollection", features: visibleSimulationAnimals.map((animal) => ({
      type: "Feature", properties: { animal_id: animal.id, species: animal.species },
      geometry: { type: "Point", coordinates: animal.coordinates }
    })) });
  }, [mapReady, visibleSimulationAnimals]);
  useEffect(() => {
    if (selectedId && !filtered.some((item) => String(item.id) === selectedId)) setSelectedId(null);
  }, [filtered, selectedId]);
  useEffect(() => {
    const map = mapRef.current;
    if (!mapReady || !map || regionCode === "all") return;
    const region = regions.find((item) => item.properties.code === regionCode);
    if (!region) return;
    const bounds = new maplibregl.LngLatBounds();
    extendGeometry(bounds, region.geometry.coordinates);
    if (!bounds.isEmpty()) map.fitBounds(bounds, { padding: 55, maxZoom: 13, duration: 500 });
  }, [mapReady, regionCode, regions]);

  return <div className="flex h-[calc(100dvh-108px)] min-h-[460px] flex-col gap-3 overflow-hidden p-4 sm:min-h-[560px]">
    <header className="flex flex-wrap items-end justify-between gap-3">
      <div><p className="text-xs font-semibold uppercase tracking-[.16em] text-forest-700">Eight forest regions · ESA WorldCover zones</p><h1 className="font-display text-3xl text-ink-900">{title}</h1><p className="mt-1 text-sm text-ink-600">{description}</p></div>
      <div className="flex flex-wrap gap-2 text-xs"><span className="rounded-control border border-line bg-paper px-3 py-2">{regions.length} forest regions</span><span className="rounded-control border border-line bg-paper px-3 py-2">{landCover.data?.features.filter((feature) => feature.properties?.kind === "land_cover").length ?? 30} land-cover zones</span><span className="rounded-control border border-line bg-paper px-3 py-2">{records.loading ? "Loading sightings…" : records.error ? "Sightings unavailable" : `${occurrences.length} sightings · ${distinctSpecies} species`}</span><span className="rounded-control border border-line bg-paper px-3 py-2">{simulated.loading ? "Loading trackers…" : `${simulationAnimals.length} simulated mammals`}</span></div>
    </header>
    <section className="flex min-h-0 flex-1 flex-col overflow-hidden rounded-panel border border-line bg-paper shadow-sm" aria-label="Historical sighting map">
      <div className="flex shrink-0 flex-wrap items-center justify-between gap-3 border-b border-line p-3">
        <label className="flex items-center gap-2 text-sm text-ink-600">Region <select className="rounded-control border border-line bg-paper px-2 py-1 text-ink-900" value={regionCode} onChange={(event) => setRegionCode(event.target.value)}><option value="all">All regions</option>{regions.map((region) => <option key={region.id} value={region.properties.code}>{region.properties.name}</option>)}</select></label>
        <div className="flex items-center gap-3"><span className="text-xs text-ink-600">{records.loading ? "Loading sightings" : records.error ? "Sightings unavailable" : `${filtered.length} sightings`} · {visibleSimulationAnimals.length} simulated</span><details className="relative"><summary className="cursor-pointer rounded-control border border-line px-3 py-1.5 text-sm text-forest-700">Filters & layers</summary><div className="absolute right-0 top-full z-50 mt-2 grid w-[min(320px,calc(100vw-48px))] gap-3 rounded-panel border border-line bg-paper p-4 shadow-md">
          <label className="grid gap-1 text-xs text-ink-600">Species <input className="rounded-control border border-line px-2 py-1.5 text-sm text-ink-900" value={speciesSearch} onChange={(event) => setSpeciesSearch(event.target.value)} placeholder="Search species" /></label>
          <label className="grid gap-1 text-xs text-ink-600">Group <select className="rounded-control border border-line px-2 py-1.5 text-sm text-ink-900" value={className} onChange={(event) => setClassName(event.target.value)}><option value="all">All groups</option>{classes.map((value) => <option key={value} value={value}>{value}</option>)}</select></label>
          <label className="grid gap-1 text-xs text-ink-600">Year <select className="rounded-control border border-line px-2 py-1.5 text-sm text-ink-900" value={year} onChange={(event) => setYear(event.target.value)}><option value="all">All years</option>{years.map((value) => <option key={value} value={value}>{value}</option>)}</select></label>
          <label className="flex items-center gap-2 text-xs text-ink-600"><input type="checkbox" checked={insideOnly} onChange={(event) => setInsideOnly(event.target.checked)} /> Full uncertainty inside region</label>
          <label className="flex items-center gap-2 text-xs text-ink-600"><input type="checkbox" checked={landCoverVisible} onChange={(event) => setLandCoverVisible(event.target.checked)} /> Show 2021 land cover</label>
          <label className="flex items-center gap-2 text-xs text-ink-600"><input type="checkbox" checked={simulationVisible} onChange={(event) => setSimulationVisible(event.target.checked)} /> Show simulated mammals</label>
          <label className="grid gap-1 text-xs text-ink-600">Simulated species <select className="rounded-control border border-line px-2 py-1.5 text-sm text-ink-900" value={simulationSpecies} onChange={(event) => setSimulationSpecies(event.target.value)}><option value="all">All species</option>{simulationSpeciesOptions.map((value) => <option key={value} value={value}>{value}</option>)}</select></label>
          {landCover.loading && <span className="text-xs text-ink-600">Loading land cover…</span>}{landCover.error && <button type="button" className="text-xs text-risk-high underline" onClick={() => { landCoverRequestedRef.current = false; setLandCoverRetry((value) => value + 1); }}>Land cover could not load · Retry</button>}
          <button className="justify-self-start text-xs text-forest-700 underline" type="button" onClick={clearFilters}>Clear filters</button>
        </div></details></div>
      </div>
      <div className="relative min-h-0 flex-1">
        <div ref={containerRef} className="absolute inset-0" />
        {areas.loading && !regions.length && <div className="pointer-events-none absolute left-1/2 top-4 z-10 -translate-x-1/2 rounded-control border border-line bg-paper/95 px-3 py-2 text-xs text-ink-600">Loading forest regions…</div>}
        {areas.error && <button type="button" onClick={areas.retry} className="absolute left-1/2 top-4 z-10 -translate-x-1/2 rounded-control border border-line bg-paper/95 px-3 py-2 text-xs text-risk-high">Forest regions unavailable · Retry</button>}
        {records.loading && <div className="pointer-events-none absolute left-1/2 top-14 z-10 -translate-x-1/2 rounded-control border border-line bg-paper/95 px-3 py-2 text-xs text-ink-600">Loading sourced sightings…</div>}
        {records.error && <button type="button" onClick={records.retry} className="absolute left-1/2 top-14 z-10 -translate-x-1/2 rounded-control border border-line bg-paper/95 px-3 py-2 text-xs text-risk-high">Sightings unavailable · Retry</button>}
        {!records.loading && !records.error && filtered.length === 0 && <div className="pointer-events-none absolute left-1/2 top-1/2 z-10 -translate-x-1/2 -translate-y-1/2 rounded-control border border-line bg-paper/95 p-3 text-sm text-ink-600">No sightings match these filters.</div>}
        <section aria-label="Movement simulation" className="absolute bottom-4 left-3 right-16 z-30 overflow-hidden rounded-xl border border-white/80 bg-paper/90 shadow-lg backdrop-blur-xl sm:left-1/2 sm:right-auto sm:w-[min(760px,calc(100%-96px))] sm:-translate-x-1/2">
          <div className="flex flex-wrap items-center gap-x-4 gap-y-2 px-4 py-3 sm:px-5">
            <span className={`relative flex h-3 w-3 shrink-0 rounded-full ${simulationStatus?.running ? "bg-forest-500" : "bg-ink-400"}`} aria-hidden="true">
              {simulationStatus?.running && <span className="absolute inset-0 animate-ping rounded-full bg-forest-500 opacity-40" />}
            </span>
            <div className="min-w-[180px] flex-1" aria-live="polite">
              <div className="text-[11px] font-semibold uppercase tracking-wide text-forest-700">Movement simulation</div>
              <div className="text-sm font-semibold text-ink-900">{simulation.loading && !simulationStatus ? "Connecting to simulator…" : simulation.error ? "Simulator unavailable" : simulationStatus?.last_error ? `GPS update failed (${simulationStatus.last_error})` : simulationStatus?.running ? "Animals are moving live on the map" : simulationStatus?.finished ? "All journeys complete · ready to replay" : "Simulation stopped"}</div>
              <div className="text-xs text-ink-600">{routeCount ? `${completedRoutes}/${routeCount} journeys complete · ` : ""}{simulationStatus?.interval_seconds ? `GPS updates every ${simulationStatus.interval_seconds} seconds` : "Live positions refresh automatically"}</div>
            </div>
            <div className="flex flex-wrap gap-1.5 text-[10px] font-medium sm:text-[11px]">
              <span className="rounded-full bg-moss-100 px-2.5 py-1 text-forest-700">{visibleSimulationAnimals.length} trackers</span>
              {simulationStatus && <><span className="rounded-full bg-[#e9f2e9] px-2.5 py-1 text-[#275e3c]">Zones · {simulationStatus.last_zone_crossings ?? 0}</span><span className="rounded-full bg-[#e8eef3] px-2.5 py-1 text-[#355a72]">Regions · {simulationStatus.last_region_crossings ?? 0}</span></>}
            </div>
            <button type="button" disabled={simulationBusy || simulation.loading || !!simulation.error || !simulationStatus} onClick={toggleSimulation} className={`rounded-control shrink-0 px-5 py-2 text-sm font-semibold text-white shadow-sm transition-opacity hover:opacity-90 disabled:cursor-not-allowed disabled:opacity-50 ${simulationStatus?.running ? "bg-ink-700" : "bg-forest-700"}`}>
              {simulationBusy ? "Updating…" : simulationStatus?.running ? "Stop" : simulationStatus?.finished ? "Replay" : "Start"}
            </button>
          </div>
          {routeCount > 0 && <div role="progressbar" aria-label="Completed animal journeys" aria-valuemin={0} aria-valuemax={routeCount} aria-valuenow={completedRoutes} className="h-1 bg-moss-100"><div className="h-full bg-forest-500 transition-[width] duration-500" style={{ width: `${Math.min(100, completedRoutes / routeCount * 100)}%` }} /></div>}
          {simulation.error && <button type="button" onClick={simulation.retry} className="px-5 pb-3 text-xs text-risk-high underline">Could not load simulator · Retry</button>}
          {simulationError && <p role="alert" className="px-5 pb-3 text-xs text-risk-high">Simulation action failed: {simulationError}</p>}
        </section>
      </div>
    </section>
  </div>;
};
