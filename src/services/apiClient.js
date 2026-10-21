const API_BASE_URL = (import.meta.env?.DEV
  ? "/api/v1"
  : import.meta.env?.VITE_API_BASE_URL || "http://127.0.0.1:8001/api/v1").replace(/\/+$/, "");
const apiUrl = (path) => {
  const normalizedPath = path.startsWith("/") ? path : `/${path}`;
  const apiPath = normalizedPath.replace(/^\/api\/v1(?=\/|$)/, "");
  return `${API_BASE_URL}${apiPath}`;
};
const getApiJson = (path, options = {}) => sendApiJson(path, options);
const API_CACHE_TTL_MS = 60000;
const apiResponseCache = new Map();
const apiInFlight = new Map();
let apiCacheGeneration = 0;
const sendApiJson = async (path, options = {}) => {
  // Render free services can take several seconds to wake after inactivity.
  const { timeoutMs = 60000, cacheMs, ...fetchOptions } = options;
  const method = (fetchOptions.method ?? "GET").toUpperCase();
  const url = apiUrl(path);
  const ttl = cacheMs ?? (method === "GET" ? API_CACHE_TTL_MS : 0);
  const cacheable = method === "GET" && ttl > 0 && !fetchOptions.signal;
  const requestGeneration = apiCacheGeneration;
  const cacheKey = `${method}:${url}`;
  if (cacheable) {
    const cached = apiResponseCache.get(cacheKey);
    if (cached && cached.expiresAt > Date.now()) return cached.value;
    if (cached) apiResponseCache.delete(cacheKey);
    if (apiInFlight.has(cacheKey)) return apiInFlight.get(cacheKey);
  }
  const request = (async () => {
    const timeout = AbortSignal.timeout(timeoutMs);
    const response = await fetch(url, {
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
    const payload = response.status === 204 ? null : await response.json();
    if (method !== "GET") {
      apiCacheGeneration += 1;
      // Simulation and alert writes do not change sourced Ooty geography or sightings.
      // Keep those larger responses warm while invalidating live operational data.
      const zoneWrite = url.startsWith(`${API_BASE_URL}/zones`);
      for (const key of apiResponseCache.keys()) {
        const staticSightings = key.startsWith(`GET:${API_BASE_URL}/research/occurrences`);
        const staticAreas = key.startsWith(`GET:${API_BASE_URL}/research/areas`) && !zoneWrite;
        if (!staticSightings && !staticAreas) apiResponseCache.delete(key);
      }
      apiInFlight.clear();
    } else if (cacheable && requestGeneration === apiCacheGeneration) {
      apiResponseCache.set(cacheKey, { value: payload, expiresAt: Date.now() + ttl });
    }
    return payload;
  })();
  if (!cacheable) return request;
  apiInFlight.set(cacheKey, request);
  try { return await request; }
  finally { if (apiInFlight.get(cacheKey) === request) apiInFlight.delete(cacheKey); }
};
const risk = (value) => {
  if (value === "safe" || value === "low" || value === "medium" || value === "high" || value === "critical" || value === "info") {
    return value;
  }
  return "info";
};
const zoneType = (value) => {
  if (["tree_cover", "grassland", "cultivated_land", "built_up", "bare_or_sparse_cover", "surface_water"].includes(value)) {
    return value;
  }
  return "tree_cover";
};
const apiAnimalToAnimal = (item) => ({
  id: item.animal_id,
  name: item.name,
  species: item.species || "unknown",
  dataOrigin: item.data_origin || "legacy_unverified",
  sourceReferenceType: item.source_reference_type || null,
  sourceReferenceName: item.source_reference_name || null,
  sourceReferenceUrl: item.source_reference_url || null,
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
    regionCode: item.study_region_code ?? null,
    regionName: item.study_region_name ?? null,
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
