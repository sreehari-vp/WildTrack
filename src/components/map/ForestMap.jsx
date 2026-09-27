import maplibregl from "maplibre-gl";
import { MapPin, Pencil, Trash2 } from "lucide-react";
import { createRoot } from "react-dom/client";
import { useEffect, useMemo, useRef, useState } from "react";
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
const ForestMap = ({
  animals,
  devices,
  zones,
  boundary,
  alertsOpenAnimalIds = [],
  alerts = [],
  movementPaths = [],
  preview = false,
  selectedAnimalId,
  selectedMovementSummary,
  onAnimalSelect,
  className = ""
}) => {
  const containerRef = useRef(null);
  const mapRef = useRef(null);
  const animalMarkers = useRef(/* @__PURE__ */ new Map());
  const clusterMarkers = useRef(/* @__PURE__ */ new Map());
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
  const [labelsVisible, setLabelsVisible] = useState(true);
  const [activeTool, setActiveTool] = useState(null);
  const [location, setLocation] = useState(null);
  const [pinDraft, setPinDraft] = useState(null);
  const [pins, setPins] = useState([]);
  const [radiusDraft, setRadiusDraft] = useState(null);
  const [drawPoints, setDrawPoints] = useState([]);
  const [drawDraft, setDrawDraft] = useState(null);
  const [zonePanel, setZonePanel] = useState(null);
  const [zoneHover, setZoneHover] = useState(null);
  const [zoneOverrides, setZoneOverrides] = useState({});
  const [deletedZoneIds, setDeletedZoneIds] = useState([]);
  const [localZones, setLocalZones] = useState([]);
  const { pushToast } = useToast();
  const allZones = useMemo(
    () => [...zones, ...localZones].filter((zone) => !deletedZoneIds.includes(zone.id)).map((zone) => ({ ...zone, ...zoneOverrides[zone.id] })),
    [deletedZoneIds, localZones, zoneOverrides, zones]
  );
  const selectedAnimal = animals.find((animal) => animal.id === selectedId);
  const selectedZone = selectedAnimal ? allZones.find((zone) => zone.id === selectedAnimal.currentZoneId) : void 0;
  const selectedDevice = selectedAnimal ? devices.find((device) => device.id === selectedAnimal.deviceId) : void 0;
  useEffect(() => setSelectedId(selectedAnimalId), [selectedAnimalId]);
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
      attributionControl: false,
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
          "fill-opacity": ["case", ["boolean", ["feature-state", "hover"], false], 0.36, 0.22]
        }
      });
      map.addLayer({
        id: "zones-line",
        type: "line",
        source: "zones",
        paint: {
          "line-color": ["get", "color"],
          "line-width": 1.5
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
      if (selectedAnimalRef.current) {
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
      setLocation(mapLocationFromPoint(point, allZonesRef.current));
      setSelectedId(void 0);
    });
    return () => {
      animalMarkers.current.forEach(({ marker, root }) => {
        root.unmount();
        marker.remove();
      });
      clusterMarkers.current.forEach(({ marker, root }) => {
        root.unmount();
        marker.remove();
      });
      pinMarkers.current.forEach((marker) => marker.remove());
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
          <span className="block text-xs text-ink-600">{animal.species === "elephant" ? "Asian elephant" : animal.species === "tiger" ? "Bengal tiger" : "Spotted deer"}</span>
          <span className="mt-1 flex items-center gap-1 text-xs text-ink-600">
            <span className={animal.status === "active" ? "h-2 w-2 rounded-full bg-[color:var(--risk-safe)]" : "h-2 w-2 rounded-full bg-ink-400"} />
            {animal.status.charAt(0).toUpperCase() + animal.status.slice(1)}
          </span>
        </span>
        {device && device.battery < 25 ? <span className="animal-marker__battery" /> : null}
      </>;
    if (!animalsVisible) {
      animalMarkers.current.forEach(({ marker, root }) => {
        root.unmount();
        marker.remove();
      });
      animalMarkers.current.clear();
      clusterMarkers.current.forEach(({ marker, root }) => {
        root.unmount();
        marker.remove();
      });
      clusterMarkers.current.clear();
      return;
    }
    if (zoom < 11.7) {
      animalMarkers.current.forEach(({ marker, root }) => {
        root.unmount();
        marker.remove();
      });
      animalMarkers.current.clear();
      const activeClusters = /* @__PURE__ */ new Set();
      ["elephant", "tiger", "deer"].forEach((species) => {
        const group = animals.filter((animal) => animal.species === species);
        if (!group.length) return;
        activeClusters.add(species);
        const center = group.reduce(
          (acc, animal) => [acc[0] + animal.coordinates[0] / group.length, acc[1] + animal.coordinates[1] / group.length],
          [0, 0]
        );
        const content = <>
            <SpeciesIcon species={species} className="h-5 w-5" />
            <span className="cluster-marker__count">{species} × {group.length}</span>
          </>;
        const existing = clusterMarkers.current.get(species);
        if (existing) {
          existing.marker.setLngLat(center);
          existing.marker.getElement().setAttribute("aria-label", `${group.length} ${species} markers`);
          existing.marker.getElement().onclick = () => {
            map.flyTo({ center, zoom: 12.5, duration: 650 });
          };
          existing.root.render(content);
        } else {
          const element = document.createElement("button");
          element.type = "button";
          element.className = "cluster-marker";
          element.setAttribute("aria-label", `${group.length} ${species} markers`);
          const root = createRoot(element);
          root.render(content);
          element.onclick = () => {
            map.flyTo({ center, zoom: 12.5, duration: 650 });
          };
          const marker = new maplibregl.Marker({ element }).setLngLat(center).addTo(map);
          clusterMarkers.current.set(species, { marker, root });
        }
      });
      clusterMarkers.current.forEach(({ marker, root }, species) => {
        if (activeClusters.has(species)) return;
        root.unmount();
        marker.remove();
        clusterMarkers.current.delete(species);
      });
      return;
    }
    clusterMarkers.current.forEach(({ marker, root }) => {
      root.unmount();
      marker.remove();
    });
    clusterMarkers.current.clear();
    const activeAnimalIds = new Set(animals.map((animal) => animal.id));
    animalMarkers.current.forEach(({ marker, root }, id) => {
      if (activeAnimalIds.has(id)) return;
      root.unmount();
      marker.remove();
      animalMarkers.current.delete(id);
    });
    animals.forEach((animal) => {
      const device = devices.find((item) => item.id === animal.deviceId);
      const existing = animalMarkers.current.get(animal.id);
      const element = existing?.marker.getElement() ?? document.createElement("button");
      element.dataset.status = animal.status;
      element.dataset.selected = selectedId === animal.id ? "true" : "false";
      element.dataset.critical = animal.risk === "critical" ? "true" : "false";
      element.style.setProperty("--marker-ring", `var(${riskCssVar(animal.risk)})`);
      element.setAttribute("aria-label", `${animal.id} ${animal.species} ${animal.status}`);
      element.title = `${animal.id} \xB7 ${animal.species} \xB7 ${animal.status}`;
      if (existing) {
        existing.marker.setLngLat(animal.coordinates);
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
      animalMarkers.current.set(animal.id, { marker, root });
    });
  }, [animals, animalsVisible, devices, mapReady, selectedId, zoom]);
  useEffect(() => {
    animalMarkers.current.forEach(({ marker }, id) => {
      marker.getElement().style.display = zoom < 11.7 ? "none" : "";
      marker.getElement().dataset.selected = selectedId === id ? "true" : "false";
    });
  }, [selectedId, zoom]);
  useEffect(() => {
    const map = mapRef.current;
    if (!mapReady || !map || !selectedId) {
      if (!selectedId) setPopupPoint(void 0);
      return;
    }
    const animal = animalsByIdRef.current.get(selectedId);
    if (!animal) return;
    map.flyTo({ center: animal.coordinates, zoom: Math.max(map.getZoom(), 13), duration: 650 });
    const point = map.project(animal.coordinates);
    setPopupPoint({ x: point.x + 22, y: point.y - 24 });
  }, [mapReady, selectedId]);
  useEffect(() => {
    const map = mapRef.current;
    if (!mapReady || !map || !selectedAnimal) return;
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
      features: movementPaths.map((path) => ({
        type: "Feature",
        properties: { id: path.id, animalId: path.animalId },
        geometry: { type: "LineString", coordinates: path.coordinates }
      }))
    });
  }, [mapReady, movementPaths]);
  useEffect(() => {
    const map = mapRef.current;
    if (!mapReady || !map) return;
    zoneLabelMarkers.current.forEach((marker) => marker.remove());
    zoneLabelMarkers.current.clear();
    if (!labelsVisible || !zonesVisible || zoom < 11.6) return;
    allZones.forEach((zone) => {
      const ring = zone.geometry.coordinates[0];
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
    pinMarkers.current.forEach((marker) => marker.remove());
    pinMarkers.current.clear();
    if (!pinsVisible) return;
    pins.forEach((pin) => {
      const element = document.createElement("div");
      element.className = "pin-marker";
      element.title = `${pin.type}: ${pin.name}`;
      const root = createRoot(element);
      root.render(<MapPin className="h-4 w-4" strokeWidth={1.75} />);
      const marker = new maplibregl.Marker({ element }).setLngLat(pin.coordinates).addTo(map);
      pinMarkers.current.set(pin.id, marker);
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
  const selectedZoneAnimals = zonePanel ? animals.filter((animal) => animal.currentZoneId === zonePanel.zone.id) : [];
  const selectedZoneAlerts = zonePanel ? alerts.filter((alert) => alert.zoneId === zonePanel.zone.id) : [];
  return <div className={`map-wrap ${className}`} data-zoomed={zoom >= 12.8 ? "true" : "false"}>
      <div ref={containerRef} className="map-container" />
      {!preview ? <>
          <div className="absolute left-4 top-4 z-20 flex items-center gap-2">
            <Input placeholder={activeTool ? `Click the map to use ${activeTool}` : "Search map"} className="w-64 bg-paper/95" />
            <Button>Filters</Button>
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
          {zonePanel ? <div className="absolute z-30 w-80 rounded-panel border border-line bg-paper p-3 shadow-md" style={{ left: Math.min(zonePanel.point.x, window.innerWidth - 380), top: Math.min(zonePanel.point.y, window.innerHeight - 360) }}>
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
                    <Button variant="ghost" onClick={() => setZonePanel({ ...zonePanel, editing: false })}>Cancel</Button>
                    <Button
    variant="primary"
    onClick={() => {
      setZoneOverrides((current) => ({ ...current, [zonePanel.zone.id]: zonePanel.zone }));
      setZonePanel({ ...zonePanel, editing: false });
      pushToast({ title: "Zone updated locally" });
    }}
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
                    <Button
    variant="danger"
    icon={<Trash2 className="h-4 w-4" strokeWidth={1.75} />}
    onClick={() => {
      if (window.confirm(`Delete ${zonePanel.zone.name}?`)) {
        setDeletedZoneIds((current) => [...current, zonePanel.zone.id]);
        setZonePanel(null);
        pushToast({ title: "Zone deleted locally" });
      }
    }}
  >
                      Delete
                    </Button>
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
    onClick={() => {
      setPins((current) => [
        ...current,
        { id: crypto.randomUUID(), name: pinDraft.name, type: pinDraft.type, coordinates: pinDraft.coordinates, createdAt: (/* @__PURE__ */ new Date()).toISOString() }
      ]);
      setPinDraft(null);
      setActiveTool(null);
      pushToast({ title: "Pin saved" });
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
    onCreate={() => {
      const newZone = {
        id: `zone-local-${Date.now()}`,
        name: radiusDraft.name,
        type: radiusDraft.type,
        risk: radiusDraft.risk,
        areaKm2: Number((Math.PI * radiusDraft.radius * radiusDraft.radius / 1e6).toFixed(2)),
        description: "Local radius zone created during this session.",
        geometry: { type: "Polygon", coordinates: [circlePolygon(radiusDraft.center, radiusDraft.radius)] }
      };
      setLocalZones((current) => [...current, newZone]);
      setRadiusDraft(null);
      setActiveTool(null);
      pushToast({
        title: "Radius zone created",
        actionLabel: "Undo",
        onAction: () => setLocalZones((current) => current.filter((zone) => zone.id !== newZone.id))
      });
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
    onClick={() => {
      if (drawPoints.length < 3 || !drawDraft.name.trim()) return;
      const newZone = {
        id: `zone-drawn-${Date.now()}`,
        name: drawDraft.name,
        type: drawDraft.type,
        risk: drawDraft.risk,
        areaKm2: 1.2,
        description: drawDraft.description,
        geometry: { type: "Polygon", coordinates: [[...drawPoints, drawPoints[0]]] }
      };
      setLocalZones((current) => [...current, newZone]);
      setDrawPoints([]);
      setDrawDraft(null);
      setActiveTool(null);
      pushToast({
        title: "Custom zone created",
        actionLabel: "Undo",
        onAction: () => setLocalZones((current) => current.filter((zone) => zone.id !== newZone.id))
      });
    }}
  >
                      Create zone
                    </Button>
                  </div>
                </div> : <div className="mt-3 flex flex-wrap gap-2">
                  <Button disabled={!drawPoints.length} onClick={() => setDrawPoints((current) => current.slice(0, -1))}>Undo point</Button>
                  <Button disabled={drawPoints.length < 3} variant="primary" onClick={() => setDrawDraft({ name: "Custom protected zone", type: "protected", risk: "high", description: "Local drawn zone created during this session." })}>Finish polygon</Button>
                  <Button variant="ghost" onClick={() => {
    setDrawPoints([]);
    setDrawDraft(null);
    setActiveTool(null);
  }}>Cancel</Button>
                </div>}
            </div> : null}
        </> : null}
      {selectedAnimal && popupPoint && !preview ? <div className="pointer-events-auto absolute z-40" style={{ left: popupPoint.x, top: popupPoint.y }}>
          <AnimalPopup
    animal={selectedAnimal}
    zone={selectedZone}
    device={selectedDevice}
    movementSummary={selectedMovementSummary}
    onViewOnMap={() => flyToAnimal(selectedAnimal)}
  />
        </div> : null}
      {alertsOpenAnimalIds.length ? <div className="absolute bottom-4 right-4 z-20 rounded-control bg-paper/95 px-3 py-2 text-xs text-ink-600 shadow-sm">
          {alertsOpenAnimalIds.length} animals need attention
        </div> : null}
    </div>;
};
export {
  ForestMap
};
