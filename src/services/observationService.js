import { apiMovementToObservations, apiObservationToObservation, getApiJson } from "./apiClient";
const query = (params = {}) => {
  const value = new URLSearchParams({ limit: String(params.limit ?? 500) });
  if (params.startTime) value.set("start_time", params.startTime);
  if (params.endTime) value.set("end_time", params.endTime);
  return value.toString();
};
export const observationService = {
  getObservations: async () => (await getApiJson("/observations?limit=500")).map(apiObservationToObservation),
  getObservationsForAnimal: async (id) => apiMovementToObservations(await getApiJson(`/animals/${encodeURIComponent(id)}/movement?limit=500`)),
  getMovementForAnimal: async (id, params = {}) => {
    const movement = await getApiJson(`/animals/${encodeURIComponent(id)}/movement?${query(params)}`);
    return { ...movement, observations: apiMovementToObservations(movement) };
  },
  getZoneHistoryForAnimal: (id, params = {}) => getApiJson(`/animals/${encodeURIComponent(id)}/zone-history?${query({ limit: 2000, ...params })}`),
  getTimelineForAnimal: (id, params = {}) => getApiJson(`/animals/${encodeURIComponent(id)}/timeline?${query({ limit: 2000, ...params })}`)
};
