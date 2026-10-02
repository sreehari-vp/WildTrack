import maplibregl from "maplibre-gl";
import { MapPin, Pencil, Trash2 } from "lucide-react";
import { createRoot } from "react-dom/client";
import { useEffect, useRef, useState } from "react";
import { boundaryFeature, circlePolygon, mapLocationFromPoint, reserveCenter, zoneFeatureCollection } from "../../utils/geo";
import { cssVar, riskCssVar, riskMeta, zoneCssVar, zoneLabels } from "../../utils/risk";
import { SpeciesIcon } from "../animals/SpeciesIcon";
import { AnimalPopup } from "../animals/AnimalPopup";
import { MapControls } from "./MapControls";
import { MapLegend } from "./MapLegend";
import { LocationCard } from "./LocationCard";
import { OfficerToolbar } from "./OfficerToolbar";
import { RadiusPanel } from "./RadiusPanel";
import { Button } from "../common/Button";
import { Input } from "../common/Input";
import { Select } from "../common/Select";
import { useToast } from "../../hooks/useToast";
import { zoneService } from "../../services/zoneService";
import { monitoringService } from "../../services/monitoringService";
const mapStyle = () => ({
  version: 8,
  sources: {
    "world-map": {
      type: "raster",
      tiles: ["https://tile.openstreetmap.org/{z}/{x}/{y}.png"],
      tileSize: 256,
      attribution: "\xA9 OpenStreetMap contributors"
    }
  },
  layers: [
    {
      id: "background",
      type: "background",
      paint: { "background-color": cssVar("--sage-50", "transparent") }
    },
    {
      id: "world-map",
      type: "raster",
      source: "world-map",
      paint: {
        "raster-opacity": 0.72,
        "raster-saturation": -0.45,
        "raster-contrast": -0.08
      }
    }
  ]
});
const moveMarkerSmoothly = (entry, destination, duration = 2600) => {
  if (entry.animationFrame) cancelAnimationFrame(entry.animationFrame);
  const start = entry.marker.getLngLat();
  const [endLng, endLat] = destination;
  if (start.lng === endLng && start.lat === endLat) return;
  const startedAt = performance.now();
  const animate = (now) => {
    const progress = Math.min((now - startedAt) / duration, 1);
    const eased = progress * (2 - progress);
    entry.marker.setLngLat([
      start.lng + (endLng - start.lng) * eased,
      start.lat + (endLat - start.lat) * eased
    ]);
    if (progress < 1) entry.animationFrame = requestAnimationFrame(animate);
    else entry.animationFrame = null;
  };
  entry.animationFrame = requestAnimationFrame(animate);
};
const ForestMap = ({
  animals,
  devices,
  zones,
  boundary,
  alertsOpenAnimalIds = [],
  hideAlertSummary = false,
  alerts = [],
  movementPaths = [],
  preview = false,
  selectedAnimalId,
  selectedZoneId,
  selectedMovementSummary,
  onAnimalSelect,
  onZonesChanged,
  className = ""
}) => {
  const containerRef = useRef(null);
  const mapRef = useRef(null);
  const animalMarkers = useRef(/* @__PURE__ */ new Map());
  const pinMarkers = useRef(/* @__PURE__ */ new Map());
  const zoneLabelMarkers = useRef(/* @__PURE__ */ new Map());
  const activeToolRef = useRef(null);
  const allZonesRef = useRef(zones);
  const animalsByIdRef = useRef(/* @__PURE__ */ new Map());
  const onAnimalSelectRef = useRef(onAnimalSelect);
  const selectedAnimalRef = useRef(void 0);
  const [mapReady, setMapReady] = useState(false);
  const [selectedId, setSelectedId] = useState(selectedAnimalId);
  const [popupPoint, setPopupPoint] = useState();
  const [zoom, setZoom] = useState(12.2);
  const [layerMode, setLayerMode] = useState("plain");
  const [boundaryVisible, setBoundaryVisible] = useState(true);
  const [zonesVisible, setZonesVisible] = useState(true);
  const [animalsVisible, setAnimalsVisible] = useState(true);
  const [pathsVisible, setPathsVisible] = useState(true);
  const [pinsVisible, setPinsVisible] = useState(true);
  const [labelsVisible, setLabelsVisible] = useState(false);
  const [search, setSearch] = useState("");
  const [speciesFilter, setSpeciesFilter] = useState("all");
  const visibleAnimals = animals.filter((animal) => Array.isArray(animal.coordinates) && animal.coordinates.every(Number.isFinite) && (speciesFilter === "all" || animal.species === speciesFilter) && `${animal.id} ${animal.name}`.toLowerCase().includes(search.toLowerCase()));
  const [activeTool, setActiveTool] = useState(null);
  const [location, setLocation] = useState(null);
  const [pinDraft, setPinDraft] = useState(null);
  const [pins, setPins] = useState([]);
  const [preferencesLoaded, setPreferencesLoaded] = useState(false);
  const [saving, setSaving] = useState(false);
  const [radiusDraft, setRadiusDraft] = useState(null);
  const [drawPoints, setDrawPoints] = useState([]);
  const [drawDraft, setDrawDraft] = useState(null);
  const [zonePanel, setZonePanel] = useState(null);
  const [zoneHover, setZoneHover] = useState(null);
  const { pushToast } = useToast();
  const allZones = zones;
  useEffect(() => {
    if (preview) return;
    let active = true;
    Promise.all([monitoringService.getPins(), monitoringService.getPreferences()]).then(([savedPins, preferences]) => {
      if (!active) return;
      setPins(savedPins);
      setLayerMode(preferences.layer_mode);
      setBoundaryVisible(preferences.boundary_visible);
      setZonesVisible(preferences.zones_visible);
      setAnimalsVisible(preferences.animals_visible);
      setPathsVisible(preferences.paths_visible);
      setPinsVisible(preferences.pins_visible);
      setLabelsVisible(preferences.labels_visible);
      setPreferencesLoaded(true);
    }).catch((error) => pushToast({ title: `Could not load map settings: ${error.message}` }));
    return () => { active = false; };
  }, [preview]);
  useEffect(() => {
    if (!preferencesLoaded || preview) return;
    const timer = window.setTimeout(() => {
      monitoringService.savePreferences({
        layer_mode: layerMode, boundary_visible: boundaryVisible, zones_visible: zonesVisible,
        animals_visible: animalsVisible, paths_visible: pathsVisible, pins_visible: pinsVisible,
        labels_visible: labelsVisible
      }).catch((error) => pushToast({ title: `Could not save map settings: ${error.message}` }));
    }, 350);
    return () => window.clearTimeout(timer);
  }, [preferencesLoaded, preview, layerMode, boundaryVisible, zonesVisible, animalsVisible, pathsVisible, pinsVisible, labelsVisible]);
  const saveZone = async (zone, isNew = false) => {
    if (saving) return;
    setSaving(true);
    try {
      const saved = isNew ? await zoneService.createZone(zone) : await zoneService.updateZone(zone);
      await onZonesChanged?.();
      setZonePanel(isNew ? null : { zone: saved, editing: false });
      pushToast({ title: isNew ? "Zone created" : "Zone updated" });
      return saved;
    } catch (error) {
      pushToast({ title: `Zone was not saved: ${error.message}` });
      return null;
    } finally {
      setSaving(false);
    }
  };
  const selectedAnimal = animals.find((animal) => animal.id === selectedId);
  const selectedZone = selectedAnimal ? allZones.find((zone) => zone.id === selectedAnimal.currentZoneId) : void 0;
  const selectedDevice = selectedAnimal ? devices.find((device) => device.id === selectedAnimal.deviceId) : void 0;
  useEffect(() => setSelectedId(selectedAnimalId), [selectedAnimalId]);
  useEffect(() => {
    if (!mapReady || !selectedZoneId) return;
    const zone = allZones.find((item) => item.id === selectedZoneId);
    if (!zone) return;
    const points = zone.geometry.type === "MultiPolygon" ? zone.geometry.coordinates.flat(2) : zone.geometry.coordinates.flat();
    const bounds = points.reduce((result, point) => result.extend(point), new maplibregl.LngLatBounds());
    mapRef.current.fitBounds(bounds, { padding: 80, duration: 650 });
    setZonePanel({ zone, point: { x: 16, y: 140 } });
  }, [mapReady, selectedZoneId, allZones]);
  useEffect(() => {
    activeToolRef.current = activeTool;
  }, [activeTool]);
  useEffect(() => {
    allZonesRef.current = allZones;
  }, [allZones]);
  useEffect(() => {
    animalsByIdRef.current = new Map(animals.map((animal) => [animal.id, animal]));
  }, [animals]);
  useEffect(() => {
    onAnimalSelectRef.current = onAnimalSelect;
  }, [onAnimalSelect]);
  useEffect(() => {
    selectedAnimalRef.current = selectedAnimal;
  }, [selectedAnimal]);
  useEffect(() => {
    if (!containerRef.current || mapRef.current) return;
    const map = new maplibregl.Map({
      container: containerRef.current,
      style: mapStyle(),
      center: reserveCenter,
      zoom: preview ? 11.3 : 12.15,
      attributionControl: { compact: true },
      dragRotate: false,
      pitchWithRotate: false,
      interactive: !preview
    });
    mapRef.current = map;
    map.on("load", () => {
      map.addSource("boundary", { type: "geojson", data: boundaryFeature(boundary) });
      map.addLayer({
        id: "boundary-line",
        type: "line",
        source: "boundary",
        paint: {
          "line-color": cssVar("--forest-700", "currentColor"),
          "line-width": 1.6,
          "line-dasharray": [2, 2]
        }
      });
      map.addSource("zones", { type: "geojson", data: zoneFeatureCollection(allZones), promoteId: "id" });
      map.addLayer({
        id: "zones-fill",
        type: "fill",
        source: "zones",
        paint: {
          "fill-color": ["get", "color"],
          "fill-opacity": ["case", ["boolean", ["feature-state", "hover"], false], 0.18, 0.04]
        }
      });
      map.addLayer({
        id: "zones-line",
        type: "line",
        source: "zones",
        paint: {
          "line-color": ["get", "color"],
          "line-width": 1.1,
          "line-opacity": 0.76
        }
      });
      map.addSource("movement-paths", {
        type: "geojson",
        data: {
          type: "FeatureCollection",
          features: movementPaths.map((path) => ({
            type: "Feature",
            properties: { id: path.id, animalId: path.animalId },
            geometry: { type: "LineString", coordinates: path.coordinates }
          }))
        }
      });
      map.addLayer({
        id: "movement-paths-line",
        type: "line",
        source: "movement-paths",
        paint: {
          "line-color": cssVar("--forest-700", "currentColor"),
          "line-width": 2,
          "line-opacity": 0.58,
          "line-dasharray": [2, 1.5]
        }
      });
      map.addSource("radius-preview", {
        type: "geojson",
        data: { type: "FeatureCollection", features: [] }
      });
      map.addLayer({
        id: "radius-preview-fill",
        type: "fill",
        source: "radius-preview",
        paint: { "fill-color": cssVar("--risk-high", "currentColor"), "fill-opacity": 0.16 }
      });
      map.addLayer({
        id: "radius-preview-line",
        type: "line",
        source: "radius-preview",
        paint: { "line-color": cssVar("--risk-high", "currentColor"), "line-width": 1.6, "line-dasharray": [2, 2] }
      });
      map.addSource("draw-preview", {
        type: "geojson",
        data: { type: "FeatureCollection", features: [] }
      });
      map.addLayer({
        id: "draw-preview-fill",
        type: "fill",
        source: "draw-preview",
        paint: { "fill-color": cssVar("--zone-protected", "currentColor"), "fill-opacity": 0.14 }
      });
      map.addLayer({
        id: "draw-preview-line",
        type: "line",
        source: "draw-preview",
        paint: { "line-color": cssVar("--zone-protected", "currentColor"), "line-width": 2, "line-dasharray": [2, 1] }
      });
      setMapReady(true);
    });
    let hoveredZoneId;
    map.on("mousemove", "zones-fill", (event) => {
      if (!event.features?.length) return;
      map.getCanvas().style.cursor = "pointer";
      const feature = event.features[0];
      if (hoveredZoneId !== void 0) {
        map.setFeatureState({ source: "zones", id: hoveredZoneId }, { hover: false });
      }
      hoveredZoneId = feature.id;
      if (hoveredZoneId !== void 0) {
        map.setFeatureState({ source: "zones", id: hoveredZoneId }, { hover: true });
      }
      setZoneHover({
        name: String(feature.properties?.name ?? "Zone"),
        type: String(feature.properties?.type ?? "safe"),
        x: event.point.x + 12,
        y: event.point.y + 12
      });
    });
    map.on("mouseleave", "zones-fill", () => {
      map.getCanvas().style.cursor = "";
      if (hoveredZoneId !== void 0) {
        map.setFeatureState({ source: "zones", id: hoveredZoneId }, { hover: false });
      }
      hoveredZoneId = void 0;
      setZoneHover(null);
    });
    map.on("click", "zones-fill", (event) => {
      if (activeToolRef.current) return;
      const id = event.features?.[0]?.properties?.id;
      const zone = allZonesRef.current.find((item) => item.id === id);
      if (!zone) return;
      setZonePanel({ zone, point: { x: event.point.x + 14, y: event.point.y + 14 } });
      setLocation(null);
      setSelectedId(void 0);
    });
    map.on("zoom", () => setZoom(map.getZoom()));
    map.on("move", () => {
      if (selectedAnimalRef.current?.coordinates?.every(Number.isFinite)) {
        const point = map.project(selectedAnimalRef.current.coordinates);
        setPopupPoint({ x: point.x + 22, y: point.y - 24 });
      }
    });
    map.on("click", (event) => {
      const target = event.originalEvent.target;
      if (target.closest(".animal-marker")) return;
      if (!activeToolRef.current && map.queryRenderedFeatures(event.point, { layers: ["zones-fill"] }).length) return;
      const point = [event.lngLat.lng, event.lngLat.lat];
      if (activeToolRef.current === "locate") {
        setLocation(mapLocationFromPoint(point, allZonesRef.current));
        setZonePanel(null);
        return;
      }
      if (activeToolRef.current === "pin") {
        setPinDraft({ coordinates: point, name: "Patrol note", type: "Observation" });
        setLocation(null);
        return;
      }
      if (activeToolRef.current === "radius") {
        setRadiusDraft({ center: point, radius: 500, name: "New restricted zone", type: "restricted", risk: "high" });
        setLocation(null);
        return;
      }
      if (activeToolRef.current === "draw") {
        setDrawPoints((current) => [...current, point]);
        setZonePanel(null);
        setLocation(null);
        return;
      }
      setLocation(null);
      setZonePanel(null);
      setSelectedId(void 0);
    });
    return () => {
      animalMarkers.current.forEach(({ marker, root, animationFrame }) => {
        if (animationFrame) cancelAnimationFrame(animationFrame);
        root.unmount();
        marker.remove();
      });
      pinMarkers.current.forEach(({ marker, root }) => { root.unmount(); marker.remove(); });
      zoneLabelMarkers.current.forEach((marker) => marker.remove());
      map.remove();
      mapRef.current = null;
    };
  }, []);
  useEffect(() => {
    const map = mapRef.current;
    if (!mapReady || !map) return;
    const source = map.getSource("zones");
    source.setData({
      type: "FeatureCollection",
      features: allZones.map((zone) => ({
        type: "Feature",
        id: zone.id,
        properties: {
          id: zone.id,
          name: zone.name,
          type: zone.type,
          risk: zone.risk,
          color: cssVar(zoneCssVar[zone.type], cssVar(riskCssVar(zone.risk), "currentColor"))
        },
        geometry: zone.geometry
      }))
    });
  }, [allZones, mapReady]);
  useEffect(() => {
    const map = mapRef.current;
    if (!mapReady || !map) return;
    const renderAnimalMarker = (animal, device) => <>
        <SpeciesIcon species={animal.species} className="h-5 w-5" />
        <span className="animal-marker__label">{animal.id}</span>
        <span className="animal-marker__tooltip">
          <strong className="block font-mono text-xs tabular">{animal.id}</strong>
          <span className="block text-xs">{animal.name}</span>
          <span className="block text-xs">{animal.speedKmh.toFixed(1)} km/h · Battery {device?.battery ?? "—"}%</span>
          <span className="block text-xs">{allZones.find((zone) => zone.id === animal.currentZoneId)?.name ?? "Outside monitored zones"}</span>
          <span className="block text-xs">Last seen: {animal.lastSeen ? new Date(animal.lastSeen).toLocaleString() : "Unknown"}</span>
          <span className="block text-xs text-ink-600">{animal.species === "elephant" ? "Asian elephant" : animal.species === "tiger" ? "Bengal tiger" : "Spotted deer"}</span>
          <span className="mt-1 flex items-center gap-1 text-xs text-ink-600">
            <span className={animal.status === "active" ? "h-2 w-2 rounded-full bg-[color:var(--risk-safe)]" : "h-2 w-2 rounded-full bg-ink-400"} />
            {animal.status.charAt(0).toUpperCase() + animal.status.slice(1)}
          </span>
        </span>
        {device && device.battery < 25 ? <span className="animal-marker__battery" /> : null}
      </>;
    if (!animalsVisible) {
      animalMarkers.current.forEach(({ marker, root, animationFrame }) => {
        if (animationFrame) cancelAnimationFrame(animationFrame);
        root.unmount();
        marker.remove();
      });
      animalMarkers.current.clear();
      return;
    }
    const activeAnimalIds = new Set(visibleAnimals.map((animal) => animal.id));
    animalMarkers.current.forEach(({ marker, root, animationFrame }, id) => {
      if (activeAnimalIds.has(id)) return;
      if (animationFrame) cancelAnimationFrame(animationFrame);
      root.unmount();
      marker.remove();
      animalMarkers.current.delete(id);
    });
    visibleAnimals.forEach((animal) => {
      const device = devices.find((item) => item.id === animal.deviceId);
      const existing = animalMarkers.current.get(animal.id);
      const element = existing?.marker.getElement() ?? document.createElement("button");
      element.dataset.status = animal.status;
      element.dataset.selected = selectedId === animal.id ? "true" : "false";
      element.dataset.critical = animal.risk === "critical" ? "true" : "false";
      element.style.setProperty("--marker-ring", `var(${riskCssVar(animal.risk)})`);
      element.setAttribute("aria-label", `${animal.id} ${animal.species} ${animal.status}`);
      if (existing) {
        moveMarkerSmoothly(existing, animal.coordinates);
        existing.root.render(renderAnimalMarker(animal, device));
        return;
      }
      element.type = "button";
      element.className = "animal-marker";
      const root = createRoot(element);
      root.render(renderAnimalMarker(animal, device));
      element.addEventListener("click", (event) => {
        event.stopPropagation();
        const currentAnimal = animalsByIdRef.current.get(animal.id);
        if (!currentAnimal) return;
        setSelectedId(currentAnimal.id);
        onAnimalSelectRef.current?.(currentAnimal);
        const point = map.project(currentAnimal.coordinates);
        setPopupPoint({ x: point.x + 22, y: point.y - 24 });
      });
      const marker = new maplibregl.Marker({ element }).setLngLat(animal.coordinates).addTo(map);
      animalMarkers.current.set(animal.id, { marker, root, animationFrame: null });
    });
  }, [animals, animalsVisible, devices, mapReady, selectedId, search, speciesFilter, allZones]);
  useEffect(() => {
    animalMarkers.current.forEach(({ marker }, id) => {
      marker.getElement().dataset.selected = selectedId === id ? "true" : "false";
    });
  }, [selectedId]);
  useEffect(() => {
    const map = mapRef.current;
    if (!mapReady || !map || !selectedId) {
      if (!selectedId) setPopupPoint(void 0);
      return;
    }
    const animal = animalsByIdRef.current.get(selectedId);
    if (!animal?.coordinates?.every(Number.isFinite)) return;
    map.flyTo({ center: animal.coordinates, zoom: Math.max(map.getZoom(), 13), duration: 650 });
    const point = map.project(animal.coordinates);
    setPopupPoint({ x: point.x + 22, y: point.y - 24 });
  }, [mapReady, selectedId]);
  useEffect(() => {
    const map = mapRef.current;
    if (!mapReady || !map || !selectedAnimal?.coordinates?.every(Number.isFinite)) return;
    const point = map.project(selectedAnimal.coordinates);
    setPopupPoint({ x: point.x + 22, y: point.y - 24 });
  }, [mapReady, selectedAnimal?.coordinates]);
  useEffect(() => {
    const map = mapRef.current;
    if (!mapReady || !map) return;
    ["zones-fill", "zones-line"].forEach((id) => map.setLayoutProperty(id, "visibility", zonesVisible ? "visible" : "none"));
    map.setLayoutProperty("boundary-line", "visibility", boundaryVisible ? "visible" : "none");
    map.setLayoutProperty("movement-paths-line", "visibility", pathsVisible ? "visible" : "none");
  }, [boundaryVisible, mapReady, pathsVisible, zonesVisible]);
  useEffect(() => {
    const map = mapRef.current;
    if (!mapReady || !map) return;
    const source = map.getSource("movement-paths");
    source.setData({
      type: "FeatureCollection",
      features: movementPaths.filter((path) => path.animalId === selectedId && path.coordinates.length >= 2).map((path) => ({
        type: "Feature",
        properties: { id: path.id, animalId: path.animalId },
        geometry: { type: "LineString", coordinates: path.coordinates }
      }))
    });
  }, [mapReady, movementPaths, selectedId]);
  useEffect(() => {
    const map = mapRef.current;
    if (!mapReady || !map) return;
    zoneLabelMarkers.current.forEach((marker) => marker.remove());
    zoneLabelMarkers.current.clear();
    if (!labelsVisible || !zonesVisible || zoom < 11.6) return;
    allZones.forEach((zone) => {
      const ring = zone.geometry.type === "MultiPolygon" ? zone.geometry.coordinates[0][0] : zone.geometry.coordinates[0];
      const center = ring.reduce(
        (acc, point) => [acc[0] + point[0] / ring.length, acc[1] + point[1] / ring.length],
        [0, 0]
      );
      const element = document.createElement("div");
      element.className = "zone-label";
      element.textContent = zone.name;
      const marker = new maplibregl.Marker({ element }).setLngLat(center).addTo(map);
      zoneLabelMarkers.current.set(zone.id, marker);
    });
  }, [allZones, labelsVisible, mapReady, zonesVisible, zoom]);
  useEffect(() => {
    const map = mapRef.current;
    if (!mapReady || !map) return;
    const colors = {
      plain: { opacity: 0.76, saturation: -0.42, contrast: -0.08 },
      terrain: { opacity: 0.86, saturation: -0.22, contrast: 0.02 },
      satellite: { opacity: 0.68, saturation: -0.7, contrast: 0.22 }
    };
    map.setPaintProperty("world-map", "raster-opacity", colors[layerMode].opacity);
    map.setPaintProperty("world-map", "raster-saturation", colors[layerMode].saturation);
    map.setPaintProperty("world-map", "raster-contrast", colors[layerMode].contrast);
    map.setPaintProperty("background", "background-color", layerMode === "satellite" ? cssVar("--forest-950", "currentColor") : cssVar("--sage-50", "transparent"));
  }, [layerMode, mapReady]);
  useEffect(() => {
    const map = mapRef.current;
    if (!mapReady || !map) return;
    pinMarkers.current.forEach(({ marker, root }) => { root.unmount(); marker.remove(); });
    pinMarkers.current.clear();
    if (!pinsVisible) return;
    pins.forEach((pin) => {
      const element = document.createElement("div");
      element.className = "pin-marker";
      element.title = `${pin.type}: ${pin.name} · click to remove`;
      element.setAttribute("role", "button");
      element.setAttribute("aria-label", `Remove ${pin.name} pin`);
      element.tabIndex = 0;
      const remove = async (event) => {
        event.stopPropagation();
        if (!window.confirm(`Remove ${pin.name} pin?`)) return;
        try {
          await monitoringService.deletePin(pin.id);
          setPins((current) => current.filter((item) => item.id !== pin.id));
          pushToast({ title: "Pin removed" });
        } catch (error) { pushToast({ title: `Could not remove pin: ${error.message}` }); }
      };
      element.addEventListener("click", remove);
      element.addEventListener("keydown", (event) => { if (event.key === "Enter" || event.key === " ") remove(event); });
      const root = createRoot(element);
      root.render(<MapPin className="h-4 w-4" strokeWidth={1.75} />);
      const marker = new maplibregl.Marker({ element }).setLngLat(pin.coordinates).addTo(map);
      pinMarkers.current.set(pin.id, { marker, root });
    });
  }, [mapReady, pins, pinsVisible]);
  useEffect(() => {
    const map = mapRef.current;
    if (!mapReady || !map) return;
    const source = map.getSource("radius-preview");
    if (!radiusDraft) {
      source.setData({ type: "FeatureCollection", features: [] });
      return;
    }
    source.setData({
      type: "FeatureCollection",
      features: [
        {
          type: "Feature",
          properties: {},
          geometry: { type: "Polygon", coordinates: [circlePolygon(radiusDraft.center, radiusDraft.radius)] }
        }
      ]
    });
  }, [mapReady, radiusDraft]);
  useEffect(() => {
    const map = mapRef.current;
    if (!mapReady || !map) return;
    const source = map.getSource("draw-preview");
    if (!drawPoints.length) {
      source.setData({ type: "FeatureCollection", features: [] });
      return;
    }
    const closed = drawPoints.length > 2 ? [...drawPoints, drawPoints[0]] : drawPoints;
    const feature = drawPoints.length > 2 ? {
      type: "Feature",
      properties: {},
      geometry: { type: "Polygon", coordinates: [closed] }
    } : {
      type: "Feature",
      properties: {},
      geometry: { type: "LineString", coordinates: closed }
    };
    source.setData({
      type: "FeatureCollection",
      features: [feature]
    });
  }, [drawPoints, mapReady]);
  const flyToAnimal = (animal) => {
    mapRef.current?.flyTo({ center: animal.coordinates, zoom: 13.2, duration: 650 });
  };
  const markerScale = Math.max(0.58, Math.min(0.78, 0.58 + (zoom - 6) / 40));
  const selectedZoneAnimals = zonePanel ? animals.filter((animal) => animal.currentZoneId === zonePanel.zone.id) : [];
  const selectedZoneAlerts = zonePanel ? alerts.filter((alert) => alert.zoneId === zonePanel.zone.id) : [];
  return <div
    className={`map-wrap ${className}`}
    data-zoomed={zoom >= 12.8 ? "true" : "false"}
    style={{
      "--animal-marker-size": `${26 * markerScale}px`,
      "--animal-icon-size": `${18 * markerScale}px`,
      "--animal-marker-border": `${Math.max(1, 2 * markerScale)}px`
    }}
  >
      <div ref={containerRef} className="map-container" />
      {!preview ? <>
          <div className="absolute left-4 top-4 z-20 flex items-center gap-2">
            <Input aria-label="Search animals" value={search} onChange={(event) => setSearch(event.target.value)} placeholder="Find animal…" className="w-40 sm:w-52 bg-paper/95" />
            <Select aria-label="Filter species" value={speciesFilter} onChange={(event) => setSpeciesFilter(event.target.value)}><option value="all">All species</option><option value="elephant">Elephants</option><option value="tiger">Tigers</option><option value="deer">Deer</option></Select>
            {activeTool ? <span className="rounded-control bg-forest-700 px-2 py-1 text-xs text-paper">Click map to place {activeTool}</span> : null}
          </div>
          <OfficerToolbar activeTool={activeTool} onChange={setActiveTool} />
          <MapControls
    onZoomIn={() => mapRef.current?.zoomIn()}
    onZoomOut={() => mapRef.current?.zoomOut()}
    onFit={() => mapRef.current?.fitBounds([[76.584, 11.354], [76.762, 11.486]], { padding: 40, duration: 650 })}
    onFullscreen={() => containerRef.current?.requestFullscreen?.()}
    layerMode={layerMode}
    setLayerMode={setLayerMode}
    zonesVisible={zonesVisible}
    setZonesVisible={setZonesVisible}
    boundaryVisible={boundaryVisible}
    setBoundaryVisible={setBoundaryVisible}
    animalsVisible={animalsVisible}
    setAnimalsVisible={setAnimalsVisible}
    pathsVisible={pathsVisible}
    setPathsVisible={setPathsVisible}
    pinsVisible={pinsVisible}
    setPinsVisible={setPinsVisible}
    labelsVisible={labelsVisible}
    setLabelsVisible={setLabelsVisible}
  />
          <MapLegend />
          {zoneHover ? <div className="zone-hover-tip" style={{ left: zoneHover.x, top: zoneHover.y }}>
              <div className="font-medium">{zoneHover.name}</div>
              <div className="text-ink-600">{zoneLabels[zoneHover.type]}</div>
            </div> : null}
          {location ? <LocationCard location={location} onClose={() => setLocation(null)} /> : null}
          {zonePanel ? <div className="absolute bottom-16 left-4 z-30 max-h-[65%] w-80 max-w-[calc(100%-32px)] overflow-auto rounded-panel border border-line bg-paper p-3 shadow-md">
              <div className="flex items-start justify-between gap-3">
                <div>
                  <div className="text-xs text-ink-400">{zoneLabels[zonePanel.zone.type]} zone</div>
                  {zonePanel.editing ? <Input
    className="mt-1"
    value={zonePanel.zone.name}
    onChange={(event) => setZonePanel({ ...zonePanel, zone: { ...zonePanel.zone, name: event.target.value } })}
  /> : <h3 className="font-display text-xl text-ink-900">{zonePanel.zone.name}</h3>}
                </div>
                <button className="text-ink-400" onClick={() => setZonePanel(null)} aria-label="Close zone panel">×</button>
              </div>
              {zonePanel.editing ? <div className="mt-3 space-y-3">
                  <Select className="w-full" value={zonePanel.zone.type} onChange={(event) => setZonePanel({ ...zonePanel, zone: { ...zonePanel.zone, type: event.target.value } })}>
                    <option value="safe">Safe</option>
                    <option value="buffer">Buffer</option>
                    <option value="restricted">Restricted</option>
                    <option value="high-risk">High risk</option>
                    <option value="water-source">Water source</option>
                    <option value="protected">Protected</option>
                  </Select>
                  <Select className="w-full" value={zonePanel.zone.risk} onChange={(event) => setZonePanel({ ...zonePanel, zone: { ...zonePanel.zone, risk: event.target.value } })}>
                    <option value="safe">Safe</option>
                    <option value="medium">Medium</option>
                    <option value="high">High</option>
                    <option value="critical">Critical</option>
                    <option value="info">Info</option>
                  </Select>
                  <Input value={zonePanel.zone.description} onChange={(event) => setZonePanel({ ...zonePanel, zone: { ...zonePanel.zone, description: event.target.value } })} />
                  <div className="flex justify-end gap-2">
                    <Button variant="ghost" onClick={() => setZonePanel(null)}>Cancel</Button>
                    <Button
    variant="primary"
    disabled={saving}
    onClick={() => saveZone(zonePanel.zone)}
  >
                      Save
                    </Button>
                  </div>
                </div> : <>
                  <dl className="mt-3 grid grid-cols-2 gap-3 text-sm">
                    <div>
                      <dt className="text-xs text-ink-400">Risk</dt>
                      <dd className={`flex items-center gap-1 ${riskMeta[zonePanel.zone.risk].className}`}>
                        {(() => {
    const Icon = riskMeta[zonePanel.zone.risk].Icon;
    return <Icon className="h-3.5 w-3.5" strokeWidth={1.75} />;
  })()}
                        {riskMeta[zonePanel.zone.risk].label}
                      </dd>
                    </div>
                    <div><dt className="text-xs text-ink-400">Animals inside</dt><dd className="font-mono tabular">{selectedZoneAnimals.length}</dd></div>
                    <div><dt className="text-xs text-ink-400">Recent alerts</dt><dd className="font-mono tabular">{selectedZoneAlerts.length}</dd></div>
                    <div><dt className="text-xs text-ink-400">Area</dt><dd className="font-mono tabular">{zonePanel.zone.areaKm2.toFixed(1)} km²</dd></div>
                  </dl>
                  <p className="mt-3 text-sm text-ink-600">{zonePanel.zone.description}</p>
                  <div className="mt-4 grid grid-cols-2 gap-2">
                    <Button onClick={() => setZonePanel({ ...zonePanel, editing: true })} icon={<Pencil className="h-4 w-4" strokeWidth={1.75} />}>Edit zone</Button>
                    {zonePanel.zone.createdInApp ? <Button
    variant="danger"
    disabled={saving}
    icon={<Trash2 className="h-4 w-4" strokeWidth={1.75} />}
    onClick={async () => {
      if (window.confirm(`Delete ${zonePanel.zone.name}?`)) {
        setSaving(true);
        try {
          await zoneService.deleteZone(zonePanel.zone.id);
          await onZonesChanged?.();
          setZonePanel(null);
          pushToast({ title: "Zone deleted" });
        } catch (error) { pushToast({ title: `Could not delete zone: ${error.message}` }); }
        finally { setSaving(false); }
      }
    }}
  >
                      Delete
                    </Button> : null}
                  </div>
                  <div className="mt-2 grid grid-cols-2 gap-2">
                    <Button onClick={() => pushToast({ title: `${selectedZoneAnimals.length} animals in ${zonePanel.zone.name}` })}>View animals</Button>
                    <Button onClick={() => pushToast({ title: `${selectedZoneAlerts.length} alerts in ${zonePanel.zone.name}` })}>View alerts</Button>
                  </div>
                </>}
            </div> : null}
          {pinDraft ? <div className="absolute left-20 top-36 z-30 w-72 rounded-panel border border-line bg-paper p-3 shadow-md">
              <h3 className="font-medium text-ink-900">Save pin</h3>
              <div className="mt-3 space-y-3">
                <Input value={pinDraft.name} onChange={(event) => setPinDraft({ ...pinDraft, name: event.target.value })} />
                <Select value={pinDraft.type} onChange={(event) => setPinDraft({ ...pinDraft, type: event.target.value })} className="w-full">
                  <option>Observation</option>
                  <option>Patrol</option>
                  <option>Camera</option>
                  <option>Hazard</option>
                </Select>
                <div className="flex justify-end gap-2">
                  <Button variant="ghost" onClick={() => setPinDraft(null)}>Cancel</Button>
                  <Button
    variant="primary"
    disabled={saving || !pinDraft.name.trim()}
    onClick={async () => {
      setSaving(true);
      try {
        const pin = await monitoringService.createPin(pinDraft);
        setPins((current) => [...current, pin]);
        setPinDraft(null);
        setActiveTool(null);
        pushToast({ title: "Pin saved" });
      } catch (error) { pushToast({ title: `Could not save pin: ${error.message}` }); }
      finally { setSaving(false); }
    }}
  >
                    Save pin
                  </Button>
                </div>
              </div>
            </div> : null}
          {radiusDraft ? <RadiusPanel
    draft={radiusDraft}
    setDraft={setRadiusDraft}
    onCancel={() => setRadiusDraft(null)}
    onCreate={async () => {
      const newZone = {
        name: radiusDraft.name,
        type: radiusDraft.type,
        risk: radiusDraft.risk,
        description: "Radius zone created on the monitoring map.",
        geometry: { type: "Polygon", coordinates: [circlePolygon(radiusDraft.center, radiusDraft.radius)] }
      };
      if (!await saveZone(newZone, true)) return;
      setRadiusDraft(null);
      setActiveTool(null);
    }}
  /> : null}
          {activeTool === "draw" ? <div className="absolute left-20 top-36 z-30 w-80 rounded-panel border border-line bg-paper p-3 shadow-md">
              <h3 className="font-medium text-ink-900">Draw custom zone</h3>
              <p className="mt-1 text-xs text-ink-600">Click the map to add points. Finish when the boundary is ready.</p>
              <div className="mt-3 rounded-control bg-moss-100 px-2 py-1 text-xs text-ink-600">{drawPoints.length} points placed</div>
              {drawDraft ? <div className="mt-3 space-y-3">
                  <Input value={drawDraft.name} onChange={(event) => setDrawDraft({ ...drawDraft, name: event.target.value })} />
                  <Select className="w-full" value={drawDraft.type} onChange={(event) => setDrawDraft({ ...drawDraft, type: event.target.value })}>
                    <option value="protected">Protected</option>
                    <option value="restricted">Restricted</option>
                    <option value="safe">Safe</option>
                    <option value="buffer">Buffer</option>
                    <option value="high-risk">High risk</option>
                    <option value="water-source">Water source</option>
                  </Select>
                  <Select className="w-full" value={drawDraft.risk} onChange={(event) => setDrawDraft({ ...drawDraft, risk: event.target.value })}>
                    <option value="high">High</option>
                    <option value="critical">Critical</option>
                    <option value="medium">Medium</option>
                    <option value="safe">Safe</option>
                    <option value="info">Info</option>
                  </Select>
                  <div className="flex justify-end gap-2">
                    <Button variant="ghost" onClick={() => setDrawDraft(null)}>Back</Button>
                    <Button
    variant="primary"
    disabled={saving}
    onClick={async () => {
      if (drawPoints.length < 3 || !drawDraft.name.trim()) return;
      const newZone = {
        name: drawDraft.name,
        type: drawDraft.type,
        risk: drawDraft.risk,
        description: drawDraft.description,
        geometry: { type: "Polygon", coordinates: [[...drawPoints, drawPoints[0]]] }
      };
      if (!await saveZone(newZone, true)) return;
      setDrawPoints([]);
      setDrawDraft(null);
      setActiveTool(null);
    }}
  >
                      Create zone
                    </Button>
                  </div>
                </div> : <div className="mt-3 flex flex-wrap gap-2">
                  <Button disabled={!drawPoints.length} onClick={() => setDrawPoints((current) => current.slice(0, -1))}>Undo point</Button>
                  <Button disabled={drawPoints.length < 3} variant="primary" onClick={() => setDrawDraft({ name: "Custom protected zone", type: "protected", risk: "high", description: "Custom zone created on the monitoring map." })}>Finish polygon</Button>
                  <Button variant="ghost" onClick={() => {
    setDrawPoints([]);
    setDrawDraft(null);
    setActiveTool(null);
  }}>Cancel</Button>
                </div>}
            </div> : null}
        </> : null}
      {selectedAnimal && popupPoint && !preview ? <div className="pointer-events-auto absolute bottom-16 left-4 z-40 max-h-[65%] overflow-auto">
          <button aria-label="Close animal details" className="absolute right-2 top-2 z-10 rounded bg-paper px-2" onClick={() => setSelectedId(undefined)}>×</button>
          <AnimalPopup
    animal={selectedAnimal}
    zone={selectedZone}
    device={selectedDevice}
    movementSummary={selectedMovementSummary}
    onViewOnMap={() => flyToAnimal(selectedAnimal)}
  />
        </div> : null}
      {!hideAlertSummary && alertsOpenAnimalIds.length ? <div className="absolute bottom-4 right-4 z-20 rounded-control bg-paper/95 px-3 py-2 text-xs text-ink-600 shadow-sm">
          {new Set(alertsOpenAnimalIds).size} animals need attention
        </div> : null}
    </div>;
};
export {
  ForestMap
};
