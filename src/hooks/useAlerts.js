import { alertService } from "../services/alertService";
import { useAsyncData } from "./useAsyncData";
const useAlerts = () => useAsyncData(alertService.getAlerts, []);
const useAlert = (id) => useAsyncData(() => alertService.getAlert(id), [id]);
export {
  useAlert,
  useAlerts
};
