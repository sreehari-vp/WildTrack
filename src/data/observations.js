import { animals } from "./animals";
const observations = animals.flatMap((animal, index) => {
  const [lng, lat] = animal.coordinates;
  return [0, 1, 2, 3].map((step) => ({
    id: `OBS-${animal.id}-${step + 1}`,
    animalId: animal.id,
    zoneId: animal.currentZoneId,
    coordinates: [lng - step * 12e-4 + index % 2 * 5e-4, lat - step * 8e-4],
    speedKmh: Math.max(0, animal.speedKmh - step * 0.4),
    recordedAt: new Date(new Date(animal.lastSeen).getTime() - step * 12 * 60 * 1e3).toISOString()
  }));
});
export {
  observations
};
