import { alertService } from "../services/alertService";
import { useAsyncData } from "./useAsyncData";
const useAlerts = (intervalMs) => useAsyncData(alertService.getAlerts, [], { intervalMs });
const useAlert = (id) => useAsyncData(() => alertService.getAlert(id), [id]);
export {
  useAlert,
  useAlerts
};
