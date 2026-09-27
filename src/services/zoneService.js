import { reserveBoundary, zones } from "../data/zones";
import { apiAnimalToAnimal, apiZoneToZone, getApiJson } from "./apiClient";
import { withDelay } from "./mockDelay";
const zoneService = {
  getZones: async () => {
    try {
      return (await getApiJson("/zones")).map(apiZoneToZone);
    } catch {
      return withDelay(zones);
    }
  },
  getBoundary: () => withDelay(reserveBoundary),
  getZone: async (id) => {
    try {
      return apiZoneToZone(await getApiJson(`/zones/${id}`));
    } catch {
      return withDelay(zones.find((zone) => zone.id === id));
    }
  },
  getAnimalsInZone: async (id) => {
    try {
      return (await getApiJson(`/zones/${id}/animals`)).map(apiAnimalToAnimal);
    } catch {
      return withDelay([]);
    }
  },
  getZoneTransitions: async (id) => {
    try {
      return getApiJson(`/zones/${id}/transitions`);
    } catch {
      return withDelay([]);
    }
  },
  createLocalZone: async (zone) => withDelay(zone, 150, 220)
};
export {
  zoneService
};
