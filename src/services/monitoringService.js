import { getApiJson, sendApiJson } from "./apiClient";

export const monitoringService = {
  getPins: () => getApiJson("/pins"),
  createPin: (pin) => sendApiJson("/pins", { method: "POST", body: JSON.stringify(pin) }),
  deletePin: (id) => sendApiJson(`/pins/${encodeURIComponent(id)}`, { method: "DELETE" }),
  getPreferences: () => getApiJson("/map/preferences"),
  savePreferences: (preferences) => sendApiJson("/map/preferences", { method: "PUT", body: JSON.stringify(preferences) }),
  getSimulationStatus: () => getApiJson("/simulation/status", { cacheMs: 0 }),
  getSummary: () => getApiJson("/monitoring/summary", { cacheMs: 0 }),
  startSimulation: () => sendApiJson("/simulation/start", { method: "POST" }),
  stopSimulation: () => sendApiJson("/simulation/stop", { method: "POST" })
};
