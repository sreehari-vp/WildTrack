import { zoneService } from "../services/zoneService";
import { useAsyncData } from "./useAsyncData";
const useZones = () => useAsyncData(zoneService.getZones, []);
const useBoundary = () => useAsyncData(zoneService.getBoundary, []);
const useZoneAnimals = (zoneId) => useAsyncData(() => zoneId ? zoneService.getAnimalsInZone(zoneId) : Promise.resolve([]), [zoneId]);
const useZoneTransitions = (zoneId) => useAsyncData(() => zoneId ? zoneService.getZoneTransitions(zoneId) : Promise.resolve([]), [zoneId]);
export {
  useBoundary,
  useZoneAnimals,
  useZoneTransitions,
  useZones
};
