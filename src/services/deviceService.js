import { devices } from "../data/devices";
import { apiAnimalToDevice, getApiJson } from "./apiClient";
import { withDelay } from "./mockDelay";
const deviceService = {
  getDevices: async () => {
    try {
      return (await getApiJson("/animals")).map(apiAnimalToDevice).filter((device) => device !== null);
    } catch {
      return withDelay(devices);
    }
  }
};
export {
  deviceService
};
