import { apiAnimalToAnimal, apiZoneToZone, getApiJson, sendApiJson } from "./apiClient";
const zonePayload = (zone) => ({
  zone_name: zone.name.trim(),
  zone_type: zone.type,
  risk_level: zone.risk,
  description: zone.description ?? "",
  geometry: zone.geometry
});
export const zoneService = {
  getZones: async () => (await getApiJson("/zones")).map(apiZoneToZone),
  getBoundary: () => getApiJson("/boundaries"),
  getZone: async (id) => apiZoneToZone(await getApiJson(`/zones/${encodeURIComponent(id)}`)),
  getAnimalsInZone: async (id) => (await getApiJson(`/zones/${encodeURIComponent(id)}/animals`)).map(apiAnimalToAnimal),
  getZoneTransitions: (id) => getApiJson(`/zones/${encodeURIComponent(id)}/transitions`),
  createZone: async (zone) => apiZoneToZone(await sendApiJson("/zones", { method: "POST", body: JSON.stringify(zonePayload(zone)) })),
  updateZone: async (zone) => apiZoneToZone(await sendApiJson(`/zones/${encodeURIComponent(zone.id)}`, { method: "PUT", body: JSON.stringify(zonePayload(zone)) })),
  deleteZone: (id) => sendApiJson(`/zones/${encodeURIComponent(id)}`, { method: "DELETE" })
};
