import { getApiJson, sendApiJson } from "./apiClient";

const query = (filters = {}) => {
  const params = new URLSearchParams();
  for (const [key, value] of Object.entries(filters)) {
    if (value) params.set(key, value);
  }
  const suffix = params.toString();
  return suffix ? `?${suffix}` : "";
};

export const networkService = {
  getSnapshot: (filters) => getApiJson(`/network${query(filters)}`, { cacheMs: 30000 }),
  getCorridor: (from, to, filters) => getApiJson(`/network/corridors/${encodeURIComponent(from)}/${encodeURIComponent(to)}${query(filters)}`, { cacheMs: 60000 }),
  getImpact: (zone, maxHops = 3) => getApiJson(`/network/impact/${encodeURIComponent(zone)}?max_hops=${maxHops}`, { cacheMs: 60000 }),
  sync: () => sendApiJson("/network/sync", { method: "POST", timeoutMs: 120000 }),
};
