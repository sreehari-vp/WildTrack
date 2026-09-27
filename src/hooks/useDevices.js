import { deviceService } from "../services/deviceService";
import { useAsyncData } from "./useAsyncData";
const useDevices = (intervalMs) => useAsyncData(deviceService.getDevices, [], { intervalMs });
export {
  useDevices
};
