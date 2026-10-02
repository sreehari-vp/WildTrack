import { getApiJson } from "./apiClient.js";

const analyticsQuery = ({ start, end, species } = {}) => {
  const params = new URLSearchParams();
  if (start) params.set("start_time", new Date(`${start}T00:00:00Z`).toISOString());
  if (end) {
    const exclusiveEnd = new Date(`${end}T00:00:00Z`);
    exclusiveEnd.setUTCDate(exclusiveEnd.getUTCDate() + 1);
    params.set("end_time", exclusiveEnd.toISOString());
  }
  if (species) params.set("species", species);
  const query = params.toString();
  return query ? `?${query}` : "";
};

const analyticsService = {
  getAnalytics: (range) => getApiJson(`/analytics${analyticsQuery(range)}`)
};
export {
  analyticsService
};
