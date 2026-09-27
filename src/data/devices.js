import { animals } from "./animals";
const models = ["Collar M2", "Collar M2", "Collar Ridge", "Collar Lite"];
const devices = animals.map((animal, index) => ({
  id: animal.deviceId,
  animalId: animal.id,
  model: models[index % models.length],
  firmware: `1.${index % 5 + 6}.${index % 9}`,
  battery: animal.id === "AE-005" ? 18 : animal.id === "AT-004" ? 22 : animal.id === "AD-012" ? 19 : 42 + index * 7 % 55,
  lastPing: animal.lastSeen
}));
export {
  devices
};
