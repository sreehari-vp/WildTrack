import { AnimalTable } from "../components/animals/AnimalTable";
import { useAnimals } from "../hooks/useAnimals";
import { useDevices } from "../hooks/useDevices";
import { useZones } from "../hooks/useZones";
import { DataState } from "./PageState";
const Animals = () => {
  const animals = useAnimals();
  const devices = useDevices();
  const zones = useZones();
  const loading = animals.loading || devices.loading || zones.loading;
  const error = animals.error || devices.error || zones.error;
  if (loading || error || !animals.data || !devices.data || !zones.data) {
    return <div className="p-6"><DataState loading={loading} error={error} onRetry={() => window.location.reload()} /></div>;
  }
  return <div className="space-y-5 p-6">
      <div><h2 className="font-display text-2xl">Animals</h2><p className="mt-1 text-sm text-ink-600">Tracked animals, device health, and current risk status.</p></div>
      <AnimalTable animals={animals.data} devices={devices.data} zones={zones.data} />
    </div>;
};
export {
  Animals
};
