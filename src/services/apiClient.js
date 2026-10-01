const API_BASE_URL = (import.meta.env.VITE_API_BASE_URL || "http://localhost:8000/api/v1").replace(/\/+$/, "");
const apiUrl = (path) => {
  const normalizedPath = path.startsWith("/") ? path : `/${path}`;
  const apiPath = normalizedPath.replace(/^\/api\/v1(?=\/|$)/, "");
  return `${API_BASE_URL}${apiPath}`;
};
const getApiJson = async (path) => {
  const response = await fetch(apiUrl(path), { headers: { Accept: "application/json" } });
  if (!response.ok) throw new Error(`API request failed: ${response.status}`);
  return response.json();
};
const sendApiJson = async (path, options = {}) => {
  const response = await fetch(apiUrl(path), {
    ...options,
    headers: {
      Accept: "application/json",
      "Content-Type": "application/json",
      ...(options.headers ?? {})
    }
  });
  if (!response.ok) throw new Error(`API request failed: ${response.status}`);
  return response.json();
};
const risk = (value) => {
  if (value === "safe" || value === "medium" || value === "high" || value === "critical" || value === "info") {
    return value;
  }
  return "info";
};
const zoneType = (value) => {
  if (value === "safe" || value === "buffer" || value === "restricted" || value === "high-risk" || value === "water-source" || value === "protected") {
    return value;
  }
  return "buffer";
};
const apiAnimalToAnimal = (item) => ({
  id: item.animal_id,
  name: item.name,
  species: item.species === "tiger" ? "tiger" : item.species === "deer" ? "deer" : "elephant",
  status: item.status === "idle" || item.status === "offline" ? item.status : "active",
  risk: risk(item.current_zone?.risk_level),
  currentZoneId: item.current_zone?.zone_id ?? "outside",
  coordinates: item.latest_observation ? [item.latest_observation.longitude, item.latest_observation.latitude] : [76.69, 11.41],
  speedKmh: item.latest_observation?.speed ?? 0,
  direction: 45,
  lastSeen: item.latest_observation?.observed_at ?? item.device?.last_seen ?? (/* @__PURE__ */ new Date()).toISOString(),
  deviceId: item.device?.device_id ?? ""
});
const apiAnimalToDevice = (item) => item.device ? {
  id: item.device.device_id,
  animalId: item.animal_id,
  model: item.device.device_type,
  firmware: "backend",
  battery: item.device.battery_level,
  lastPing: item.device.last_seen ?? item.latest_observation?.observed_at ?? (/* @__PURE__ */ new Date()).toISOString()
} : null;
const apiObservationToObservation = (item) => ({
  id: item.observation_id,
  animalId: item.animal_id,
  zoneId: "",
  coordinates: [item.longitude, item.latitude],
  speedKmh: item.speed,
  recordedAt: item.observed_at
});
const apiMovementToObservations = (movement) => movement.points.map((point, index) => ({
  id: point.observation_id ?? `MOVE-${movement.animal_id}-${index}`,
  animalId: movement.animal_id,
  zoneId: point.zone?.zone_id ?? "",
  coordinates: [point.longitude, point.latitude],
  speedKmh: point.speed ?? 0,
  recordedAt: point.timestamp,
  distanceFromPreviousMeters: point.distance_from_previous_meters ?? 0,
  sequence: index
}));
const apiZoneToZone = (item) => {
  const coordinates = item.geometry.type === "MultiPolygon" ? item.geometry.coordinates[0] : item.geometry.coordinates;
  return {
    id: item.zone_id,
    name: item.zone_name,
    type: zoneType(item.zone_type),
    risk: risk(item.risk_level),
    areaKm2: 0,
    description: item.description ?? "",
    geometry: {
      type: "Polygon",
      coordinates
    }
  };
};
export {
  apiAnimalToAnimal,
  apiAnimalToDevice,
  apiMovementToObservations,
  apiObservationToObservation,
  apiUrl,
  apiZoneToZone,
  getApiJson,
  sendApiJson
};
