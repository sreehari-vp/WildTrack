import { animals } from "../data/animals";
import { devices } from "../data/devices";
import { apiAnimalToAnimal, getApiJson } from "./apiClient";
import { withDelay } from "./mockDelay";
const animalService = {
  getAnimals: async () => {
    try {
      return (await getApiJson("/animals")).map(apiAnimalToAnimal);
    } catch {
      return withDelay(animals);
    }
  },
  getAnimal: async (id) => {
    try {
      return apiAnimalToAnimal(await getApiJson(`/animals/${id}`));
    } catch {
      const animal = animals.find((item) => item.id === id);
      return withDelay(animal);
    }
  },
  getDeviceForAnimal: async (animal) => withDelay(devices.find((device) => device.id === animal.deviceId))
};
export {
  animalService
};
