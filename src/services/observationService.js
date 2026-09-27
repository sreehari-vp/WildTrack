import { observations } from "../data/observations";
import { apiMovementToObservations, apiObservationToObservation, getApiJson } from "./apiClient";
import { withDelay } from "./mockDelay";
const movementQuery = (params = {}) => {
  const query = new URLSearchParams();
  query.set("limit", String(params.limit ?? 500));
  if (params.startTime) query.set("start_time", params.startTime);
  if (params.endTime) query.set("end_time", params.endTime);
  return query.toString();
};
const observationService = {
  getObservations: async () => {
    try {
      return (await getApiJson("/observations?limit=500")).map(apiObservationToObservation);
    } catch {
      return withDelay(observations);
    }
  },
  getObservationsForAnimal: async (animalId) => {
    try {
      return apiMovementToObservations(await getApiJson(`/animals/${animalId}/movement?limit=500`));
    } catch {
      return withDelay(observations.filter((observation) => observation.animalId === animalId));
    }
  },
  getMovementForAnimal: async (animalId, params = {}) => {
    try {
      const movement = await getApiJson(`/animals/${animalId}/movement?${movementQuery(params)}`);
      return { ...movement, observations: apiMovementToObservations(movement) };
    } catch {
      const fallback = observations.filter((observation) => observation.animalId === animalId);
      return withDelay({
        animal_id: animalId,
        points: [],
        observations: fallback,
        total_distance_meters: 0,
        movement_duration_seconds: 0,
        started_at: fallback[0]?.recordedAt ?? null,
        ended_at: fallback.at(-1)?.recordedAt ?? null
      });
    }
  },
  getZoneHistoryForAnimal: async (animalId, params = {}) => {
    try {
      return getApiJson(`/animals/${animalId}/zone-history?${movementQuery({ ...params, limit: params.limit ?? 2000 })}`);
    } catch {
      return withDelay({ animal_id: animalId, segments: [], transitions: [] });
    }
  },
  getTimelineForAnimal: async (animalId, params = {}) => {
    try {
      return getApiJson(`/animals/${animalId}/timeline?${movementQuery({ ...params, limit: params.limit ?? 2000 })}`);
    } catch {
      return withDelay({ animal_id: animalId, events: [] });
    }
  }
};
export {
  observationService
};
