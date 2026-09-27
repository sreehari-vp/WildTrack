import { animalService } from "../services/animalService";
import { useAsyncData } from "./useAsyncData";
const useAnimals = (intervalMs) => useAsyncData(animalService.getAnimals, [], { intervalMs });
const useAnimal = (id) => useAsyncData(() => animalService.getAnimal(id), [id]);
export {
  useAnimal,
  useAnimals
};
