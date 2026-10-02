import { apiAnimalToAnimal, apiAnimalToDevice, getApiJson } from "./apiClient";
export const animalService = {
  getAnimals: async () => (await getApiJson("/animals")).map(apiAnimalToAnimal),
  getAnimal: async (id) => apiAnimalToAnimal(await getApiJson(`/animals/${encodeURIComponent(id)}`)),
  getDeviceForAnimal: async (animal) => apiAnimalToDevice(await getApiJson(`/animals/${encodeURIComponent(animal.id)}`))
};
