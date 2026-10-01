import { getApiJson, sendApiJson } from "./apiClient";

const alertTypeTitle = (value) => value.split("_").map((part) => part.charAt(0).toUpperCase() + part.slice(1)).join(" ");

const apiAlertToAlert = (item) => ({
  id: item.alert_id,
  type: item.alert_type,
  title: alertTypeTitle(item.alert_type),
  animalId: item.animal_id,
  zoneId: item.zone_id ?? "",
  severity: item.severity,
  risk: item.severity === "critical" ? "critical" : item.severity === "high" ? "high" : item.severity === "medium" ? "medium" : "info",
  status: item.status,
  trigger: item.rule_name ?? alertTypeTitle(item.alert_type),
  timestamp: item.created_at,
  description: item.message,
  animalName: item.animal_name,
  zoneName: item.zone_name
});

const alertService = {
  getAlerts: async () => {
    const alerts = await getApiJson("/alerts?limit=200");
    return alerts.map(apiAlertToAlert);
  },
  getAlert: async (id) => apiAlertToAlert(await getApiJson(`/alerts/${id}`)),
  resolveAlert: async (id) => apiAlertToAlert(await sendApiJson(`/alerts/${id}`, {
    method: "PATCH",
    body: JSON.stringify({ status: "resolved" })
  })),
  acknowledgeAlert: async (id) => apiAlertToAlert(await sendApiJson(`/alerts/${id}`, {
    method: "PATCH",
    body: JSON.stringify({ status: "acknowledged" })
  }))
};

export {
  alertService
};
