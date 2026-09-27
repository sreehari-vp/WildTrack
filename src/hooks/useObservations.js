import { observationService } from "../services/observationService";
import { useAsyncData } from "./useAsyncData";
const useObservations = (intervalMs) => useAsyncData(observationService.getObservations, [], { intervalMs });
const useObservationsForAnimal = (animalId) => useAsyncData(() => observationService.getObservationsForAnimal(animalId), [animalId]);
const useMovementForAnimal = (animalId, params = {}) => useAsyncData(
  () => animalId ? observationService.getMovementForAnimal(animalId, params) : Promise.resolve(null),
  [animalId, params.startTime, params.endTime, params.limit]
);
const useZoneHistoryForAnimal = (animalId, params = {}) => useAsyncData(
  () => animalId ? observationService.getZoneHistoryForAnimal(animalId, params) : Promise.resolve({ animal_id: animalId, segments: [], transitions: [] }),
  [animalId, params.startTime, params.endTime, params.limit]
);
const useTimelineForAnimal = (animalId, params = {}) => useAsyncData(
  () => animalId ? observationService.getTimelineForAnimal(animalId, params) : Promise.resolve({ animal_id: animalId, events: [] }),
  [animalId, params.startTime, params.endTime, params.limit]
);
export {
  useMovementForAnimal,
  useObservations,
  useObservationsForAnimal,
  useTimelineForAnimal,
  useZoneHistoryForAnimal
};
