import maplibregl from "maplibre-gl";
import { useEffect, useMemo, useRef, useState } from "react";
import { useAsyncData } from "../hooks/useAsyncData";
import { researchService } from "../services/researchService";
import { animalService } from "../services/animalService";
import { monitoringService } from "../services/monitoringService";
import { DataState } from "./PageState";

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

export const FieldRecords = ({ defaultLandCover = false }) => {
  const areas = useAsyncData(() => researchService.getAreas(), []);
  const records = useAsyncData(researchService.getOccurrences, []);
  const simulated = useAsyncData(animalService.getAnimals, [], { intervalMs: 3000 });
  const simulation = useAsyncData(monitoringService.getSimulationStatus, [], { intervalMs: 3000 });
  const [simulationBusy, setSimulationBusy] = useState(false);
  const [simulationError, setSimulationError] = useState(null);
  const [simulationVisible, setSimulationVisible] = useState(true);
  const [simulationSpecies, setSimulationSpecies] = useState("all");
  const [selectedAnimalId, setSelectedAnimalId] = useState(null);
  const [landCoverVisible, setLandCoverVisible] = useState(defaultLandCover);
  const [landCover, setLandCover] = useState({ data: null, loading: false, error: null });
  const [regionCode, setRegionCode] = useState("all");
  const [speciesSearch, setSpeciesSearch] = useState("");
  const [className, setClassName] = useState("all");
  const [year, setYear] = useState("all");
  const [insideOnly, setInsideOnly] = useState(false);
  const [selectedId, setSelectedId] = useState(null);
  const [selectedArea, setSelectedArea] = useState(null);
  const [mapReady, setMapReady] = useState(false);
  const containerRef = useRef(null);
  const mapRef = useRef(null);
  const popupRef = useRef(null);
  const recordsByIdRef = useRef(new Map());
  const animalsByIdRef = useRef(new Map());

  useEffect(() => {
    if (!landCoverVisible || landCover.data || landCover.loading) return;
    setLandCover((current) => ({ ...current, loading: true, error: null }));
    researchService.getAreas(true).then((data) => {
      setLandCover({ data, loading: false, error: null });
    }).catch((error) => {
      setLandCover({ data: null, loading: false, error });
    });
  }, [landCoverVisible, landCover.data]);

  const regions = useMemo(() => areas.data?.features ?? [], [areas.data]);
  const occurrences = useMemo(() => records.data?.occurrences ?? [], [records.data]);
  const simulationAnimals = useMemo(() => (simulated.data ?? []).filter((animal) => animal.id.startsWith("SIM-V2-")), [simulated.data]);
  const simulationSpeciesOptions = useMemo(() => [...new Set(simulationAnimals.map((animal) => animal.species))].sort(), [simulationAnimals]);
  const visibleSimulationAnimals = useMemo(() => simulationAnimals.filter((animal) =>
    simulationVisible && (simulationSpecies === "all" || animal.species === simulationSpecies)
    && animal.coordinates.every(Number.isFinite)
  ), [simulationAnimals, simulationVisible, simulationSpecies]);
  animalsByIdRef.current = new Map(simulationAnimals.map((animal) => [animal.id, animal]));
  const selectedAnimal = simulationAnimals.find((animal) => animal.id === selectedAnimalId);
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
  const selected = filtered.find((item) => String(item.id) === selectedId);
  const distinctSpecies = new Set(occurrences.map((item) => item.species)).size;
  const areaFeatures = landCoverVisible && landCover.data ? landCover.data.features : regions;
  const clearFilters = () => { setRegionCode("all"); setSpeciesSearch(""); setClassName("all"); setYear("all"); setInsideOnly(false); setSimulationSpecies("all"); };
  const toggleSimulation = async () => {
    if (simulationBusy) return;
    setSimulationBusy(true);
    setSimulationError(null);
    try {
      if (simulation.data?.running) await monitoringService.stopSimulation();
      else await monitoringService.startSimulation();
      await Promise.allSettled([simulation.refresh(), simulated.refresh()]);
    } catch (error) {
      setSimulationError(error.message);
    } finally {
      setSimulationBusy(false);
    }
  };

  useEffect(() => {
    if (!regions.length || !containerRef.current || mapRef.current) return;
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
    popupRef.current = new maplibregl.Popup({ closeButton: false, closeOnClick: false, offset: 10 });
    map.addControl(new maplibregl.NavigationControl({ showCompass: false }), "bottom-right");
    map.on("load", () => {
      map.addLayer({ id: "region-fill", type: "fill", source: "areas", filter: ["==", ["get", "kind"], "region"], paint: { "fill-color": "#53745d", "fill-opacity": 0.08 } });
      map.addLayer({ id: "land-cover-fill", type: "fill", source: "areas", filter: ["==", ["get", "kind"], "land_cover"], paint: { "fill-color": landCoverColor, "fill-opacity": 0.4 } });
      map.addLayer({ id: "region-line", type: "line", source: "areas", filter: ["==", ["get", "kind"], "region"], paint: { "line-color": "#315d40", "line-width": 1.5 } });
      map.addLayer({ id: "record-dots", type: "circle", source: "records", paint: { "circle-radius": ["interpolate", ["linear"], ["zoom"], 8, 2.3, 13, 3.4, 16, 4.2], "circle-color": "#22573b", "circle-stroke-color": "#fff8e6", "circle-stroke-width": 1 } });
      map.addLayer({ id: "simulated-dots", type: "circle", source: "simulated", paint: {
        "circle-radius": ["interpolate", ["linear"], ["zoom"], 8, 2.5, 13, 4, 16, 5],
        "circle-color": ["match", ["get", "species"], "Elephas maximus", "#3b78a3", "Panthera tigris", "#c45f31", "Nilgiritragus hylocrius", "#8564a5", "#d49b36"],
        "circle-stroke-color": "#102e25", "circle-stroke-width": 0.8
      } });
      map.addLayer({ id: "selected-record", type: "circle", source: "records", filter: ["==", ["get", "record_id"], ""], paint: { "circle-radius": 7, "circle-color": "#123b2b", "circle-stroke-color": "#eacb74", "circle-stroke-width": 2.5 } });
      map.getSource("areas").setData({ type: "FeatureCollection", features: regions });
      const bounds = new maplibregl.LngLatBounds();
      regions.forEach((region) => extendGeometry(bounds, region.geometry.coordinates));
      if (!bounds.isEmpty()) map.fitBounds(bounds, { padding: 48, maxZoom: 12, duration: 0 });
      setMapReady(true);
    });
    map.on("click", "record-dots", (event) => {
      const id = event.features?.[0]?.properties?.record_id;
      if (id != null) { setSelectedId(String(id)); setSelectedArea(null); setSelectedAnimalId(null); }
    });
    map.on("click", "simulated-dots", (event) => {
      const id = event.features?.[0]?.properties?.animal_id;
      if (id != null) { setSelectedAnimalId(String(id)); setSelectedId(null); setSelectedArea(null); }
    });
    for (const layer of ["region-fill", "land-cover-fill"]) {
      map.on("click", layer, (event) => {
        if (map.queryRenderedFeatures(event.point, { layers: ["record-dots", "simulated-dots"] }).length) return;
        const feature = event.features?.[0];
        if (feature) { setSelectedArea(feature.properties); setSelectedId(null); }
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
    return () => { popupRef.current?.remove(); map.remove(); mapRef.current = null; setMapReady(false); };
  }, [regions.length]);

  useEffect(() => {
    const map = mapRef.current;
    if (!mapReady || !map) return;
    map.getSource("areas")?.setData({ type: "FeatureCollection", features: areaFeatures });
  }, [mapReady, areaFeatures]);
  useEffect(() => {
    const map = mapRef.current;
    if (!mapReady || !map) return;
    map.getSource("records")?.setData({ type: "FeatureCollection", features: filtered.map((item) => ({
      type: "Feature", properties: { record_id: String(item.id) },
      geometry: { type: "Point", coordinates: [item.longitude, item.latitude] }
    })) });
    map.setFilter("selected-record", ["==", ["get", "record_id"], selectedId ?? ""]);
  }, [mapReady, filtered, selectedId]);
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

  if (areas.loading || records.loading || areas.error || records.error || !areas.data || !records.data) {
    return <div className="p-6"><DataState loading={areas.loading || records.loading} error={areas.error || records.error} onRetry={() => { areas.retry(); records.retry(); }} /></div>;
  }
  return <div className="space-y-5 p-6">
    <header className="flex flex-wrap items-end justify-between gap-3">
      <div><p className="text-xs font-semibold uppercase tracking-[.16em] text-forest-700">Source-backed Ooty geography</p><h1 className="font-display text-3xl text-ink-900">Ooty Forest Map</h1><p className="mt-1 text-sm text-ink-600">Green dots are dated public mammal sightings. Coloured dots are synthetic trackers; their positions and movement are simulated.</p></div>
      <div className="flex flex-wrap gap-2 text-xs"><span className="rounded-control border border-line bg-paper px-3 py-2">{regions.length} forest regions</span><span className="rounded-control border border-line bg-paper px-3 py-2">{occurrences.length} sightings · {distinctSpecies} species</span><span className="rounded-control border border-line bg-paper px-3 py-2">{simulationAnimals.length} simulated mammals</span></div>
    </header>
    <section className="rounded-panel border border-line bg-paper shadow-sm" aria-label="Historical sighting map">
      <div className="flex flex-wrap items-center justify-between gap-3 border-b border-line p-3">
        <label className="flex items-center gap-2 text-sm text-ink-600">Region <select className="rounded-control border border-line bg-paper px-2 py-1 text-ink-900" value={regionCode} onChange={(event) => { setRegionCode(event.target.value); setSelectedArea(null); }}><option value="all">All regions</option>{regions.map((region) => <option key={region.id} value={region.properties.code}>{region.properties.name}</option>)}</select></label>
        <div className="flex items-center gap-3"><span className="text-xs text-ink-600">{filtered.length} sightings · {visibleSimulationAnimals.length} simulated</span><button type="button" disabled={simulationBusy || !simulationAnimals.length} onClick={toggleSimulation} className="rounded-control border border-line px-3 py-1.5 text-sm text-forest-700 disabled:opacity-50">{simulation.data?.running ? "Stop movement" : "Start movement"}</button><details className="relative"><summary className="cursor-pointer rounded-control border border-line px-3 py-1.5 text-sm text-forest-700">Filters & layers</summary><div className="absolute right-0 top-full z-50 mt-2 grid w-[min(320px,calc(100vw-48px))] gap-3 rounded-panel border border-line bg-paper p-4 shadow-md">
          <label className="grid gap-1 text-xs text-ink-600">Species <input className="rounded-control border border-line px-2 py-1.5 text-sm text-ink-900" value={speciesSearch} onChange={(event) => setSpeciesSearch(event.target.value)} placeholder="Search species" /></label>
          <label className="grid gap-1 text-xs text-ink-600">Group <select className="rounded-control border border-line px-2 py-1.5 text-sm text-ink-900" value={className} onChange={(event) => setClassName(event.target.value)}><option value="all">All groups</option>{classes.map((value) => <option key={value} value={value}>{value}</option>)}</select></label>
          <label className="grid gap-1 text-xs text-ink-600">Year <select className="rounded-control border border-line px-2 py-1.5 text-sm text-ink-900" value={year} onChange={(event) => setYear(event.target.value)}><option value="all">All years</option>{years.map((value) => <option key={value} value={value}>{value}</option>)}</select></label>
          <label className="flex items-center gap-2 text-xs text-ink-600"><input type="checkbox" checked={insideOnly} onChange={(event) => setInsideOnly(event.target.checked)} /> Full uncertainty inside region</label>
          <label className="flex items-center gap-2 text-xs text-ink-600"><input type="checkbox" checked={landCoverVisible} onChange={(event) => setLandCoverVisible(event.target.checked)} /> Show 2021 land cover</label>
          <label className="flex items-center gap-2 text-xs text-ink-600"><input type="checkbox" checked={simulationVisible} onChange={(event) => setSimulationVisible(event.target.checked)} /> Show simulated mammals</label>
          <label className="grid gap-1 text-xs text-ink-600">Simulated species <select className="rounded-control border border-line px-2 py-1.5 text-sm text-ink-900" value={simulationSpecies} onChange={(event) => setSimulationSpecies(event.target.value)}><option value="all">All species</option>{simulationSpeciesOptions.map((value) => <option key={value} value={value}>{value}</option>)}</select></label>
          {landCover.loading && <span className="text-xs text-ink-600">Loading land cover…</span>}{landCover.error && <span className="text-xs text-risk-high">Land cover could not load.</span>}
          {simulationError && <span className="text-xs text-risk-high">Simulation: {simulationError}</span>}
          <button className="justify-self-start text-xs text-forest-700 underline" type="button" onClick={clearFilters}>Clear filters</button>
        </div></details></div>
      </div>
      <div className="grid lg:grid-cols-[minmax(0,1fr)_340px]">
        <div className="relative min-h-[480px]"><div ref={containerRef} className="absolute inset-0" />{filtered.length === 0 && <div className="pointer-events-none absolute left-1/2 top-1/2 -translate-x-1/2 -translate-y-1/2 rounded-control border border-line bg-paper/95 p-3 text-sm text-ink-600">No sightings match these filters.</div>}</div>
        <aside className="max-h-[560px] overflow-auto border-t border-line p-4 lg:border-l lg:border-t-0" aria-label="Sighting details">
          {selectedAnimal ? <div className="space-y-3"><p className="text-xs font-semibold uppercase tracking-wide text-forest-700">Simulated mammal</p><h2 className="font-display text-xl">{selectedAnimal.name}</h2><p className="text-sm text-ink-600">{selectedAnimal.species} · {selectedAnimal.id}</p><p className="text-xs text-ink-600">Generated GPS position: {selectedAnimal.coordinates[1]?.toFixed(5)}, {selectedAnimal.coordinates[0]?.toFixed(5)}</p><p className="text-xs text-ink-600">This is a scenario tracker, not a real animal or field observation.</p></div> : selected ? <div className="space-y-3"><p className="text-xs font-semibold uppercase tracking-wide text-forest-700">Historical sighting</p><h2 className="font-display text-xl">{selected.species}</h2><p className="text-sm text-ink-600">{readableDate(selected.source_observed_at)} · {selected.regions.map((region) => region.name).join(", ")}</p><p className="text-xs text-ink-600">Reported point: {selected.latitude.toFixed(5)}, {selected.longitude.toFixed(5)} · ±{Math.round(Number(selected.coordinate_uncertainty_m))} m</p>{selected.regions.some((region) => region.uncertainty_crosses_boundary) && <p className="text-xs text-ink-600">The location uncertainty crosses a study-region edge.</p>}<div className="border-t border-line pt-3 text-xs text-ink-600"><p>{selected.dataset_title}</p><p>DOI: {selected.dataset_doi}</p><p>Licence: {selected.license_uri}{selected.noncommercial_only ? " · non-commercial use" : ""}</p></div><a className="inline-block text-sm text-forest-700 underline" href={selected.source_url} target="_blank" rel="noreferrer">Open source record</a></div>
            : selectedArea ? <div className="space-y-2"><p className="text-xs font-semibold uppercase tracking-wide text-forest-700">{selectedArea.kind === "region" ? "Study region" : "2021 land cover"}</p><h2 className="font-display text-xl">{selectedArea.name}</h2><p className="text-sm text-ink-600">{selectedArea.description}</p><p className="text-xs text-ink-600">Area: {Number(selectedArea.area_sq_km).toFixed(2)} km² · {selectedArea.data_source}</p><a className="text-sm text-forest-700 underline" href={selectedArea.source_url} target="_blank" rel="noreferrer">Source details</a></div>
            : <div className="space-y-2"><p className="text-xs font-semibold uppercase tracking-wide text-forest-700">Explore the evidence</p><h2 className="font-display text-xl">Select a sighting</h2><p className="text-sm text-ink-600">Small dots mark published observation coordinates. Select one for its date, uncertainty, dataset and licence.</p></div>}
          <div className="mt-5 border-t border-line pt-3"><h3 className="mb-2 text-xs font-semibold uppercase tracking-wide text-ink-600">Matching records</h3><div className="max-h-56 space-y-1 overflow-auto">{filtered.map((item) => <button key={item.id} type="button" onClick={() => { setSelectedId(String(item.id)); setSelectedArea(null); mapRef.current?.flyTo({ center: [item.longitude, item.latitude], zoom: Math.max(mapRef.current.getZoom(), 12), duration: 450 }); }} className={`flex w-full justify-between gap-2 rounded-control px-2 py-1.5 text-left text-xs hover:bg-moss-100 ${selectedId === String(item.id) ? "bg-moss-100" : ""}`}><span className="truncate">{item.species}</span><span className="shrink-0 text-ink-600">{readableDate(item.source_observed_at)}</span></button>)}</div></div>
        </aside>
      </div>
    </section>
  </div>;
};
