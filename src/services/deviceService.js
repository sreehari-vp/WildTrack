import { apiAnimalToDevice, getApiJson } from "./apiClient";
export const deviceService = {
  getDevices: async () => (await getApiJson("/animals")).map(apiAnimalToDevice).filter(Boolean)
};
