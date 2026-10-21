import { apiAnimalToAnimal, apiAnimalToDevice, getApiJson } from "./apiClient";
export const animalService = {
  getAnimals: async () => (await getApiJson("/animals", { cacheMs: 0 })).map(apiAnimalToAnimal),
  getAnimal: async (id) => apiAnimalToAnimal(await getApiJson(`/animals/${encodeURIComponent(id)}`, { cacheMs: 0 })),
  getDeviceForAnimal: async (animal) => apiAnimalToDevice(await getApiJson(`/animals/${encodeURIComponent(animal.id)}`, { cacheMs: 0 }))
};
