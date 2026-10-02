const API_BASE_URL = (import.meta.env?.DEV
  ? "/api/v1"
  : import.meta.env?.VITE_API_BASE_URL || "http://127.0.0.1:8001/api/v1").replace(/\/+$/, "");
const apiUrl = (path) => {
  const normalizedPath = path.startsWith("/") ? path : `/${path}`;
  const apiPath = normalizedPath.replace(/^\/api\/v1(?=\/|$)/, "");
  return `${API_BASE_URL}${apiPath}`;
};
const getApiJson = (path, options = {}) => sendApiJson(path, options);
const sendApiJson = async (path, options = {}) => {
  const { timeoutMs = 15000, ...fetchOptions } = options;
  const timeout = AbortSignal.timeout(timeoutMs);
  const response = await fetch(apiUrl(path), {
    ...fetchOptions,
    signal: options.signal ? AbortSignal.any([timeout, options.signal]) : timeout,
    headers: {
      Accept: "application/json",
      "Content-Type": "application/json",
      ...(options.headers ?? {})
    }
  });
  if (!response.ok) {
    let detail;
    try { detail = (await response.json()).detail; } catch { /* The server may return HTML. */ }
    if (response.status === 405) {
      throw new Error("This API does not support this save action. Restart the WildTrack backend from the same project folder as the frontend.");
    }
    throw new Error(typeof detail === "string" ? detail : `The server could not complete this request (${response.status}).`);
  }
  return response.status === 204 ? null : response.json();
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
  coordinates: item.latest_observation ? [item.latest_observation.longitude, item.latest_observation.latitude] : [null, null],
  speedKmh: item.latest_observation?.speed ?? 0,
  direction: null,
  lastSeen: item.latest_observation?.observed_at ?? item.device?.last_seen ?? null,
  deviceId: item.device?.device_id ?? ""
});
const apiAnimalToDevice = (item) => item.device ? {
  id: item.device.device_id,
  animalId: item.animal_id,
  model: item.device.device_type,
  firmware: "backend",
  battery: item.device.battery_level,
  lastPing: item.device.last_seen ?? item.latest_observation?.observed_at ?? null
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
  return {
    id: item.zone_id,
    name: item.zone_name,
    type: zoneType(item.zone_type),
    risk: risk(item.risk_level),
    areaKm2: item.area_km2 ?? 0,
    createdInApp: item.created_in_app ?? false,
    description: item.description ?? "",
    geometry: item.geometry
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
