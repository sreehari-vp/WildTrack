import { alerts } from "../data/alerts";
import { withDelay } from "./mockDelay";
let alertState = alerts;
const alertService = {
  getAlerts: () => withDelay(alertState),
  getAlert: async (id) => withDelay(alertState.find((alert) => alert.id === id)),
  resolveAlert: async (id) => {
    alertState = alertState.map(
      (alert) => alert.id === id ? { ...alert, status: "resolved" } : alert
    );
    return withDelay(alertState.find((alert) => alert.id === id));
  },
  restoreAlert: async (id) => {
    alertState = alertState.map((alert) => alert.id === id ? { ...alert, status: "open" } : alert);
    return withDelay(alertState.find((alert) => alert.id === id));
  }
};
export {
  alertService
};
