import { useState } from "react";
import { Button } from "../components/common/Button";
import { Select } from "../components/common/Select";
import { useToast } from "../hooks/useToast";
const Settings = () => {
  const { pushToast } = useToast();
  const [units, setUnits] = useState("km");
  const [layer, setLayer] = useState("plain");
  const [notify, setNotify] = useState(true);
  return <div className="max-w-3xl space-y-5 p-6">
      <div><h2 className="font-display text-2xl">Settings</h2><p className="mt-1 text-sm text-ink-600">Local preferences for this monitoring session.</p></div>
      <section className="surface divide-y divide-line">
        <div className="flex items-center justify-between gap-4 p-4">
          <div><h3 className="font-medium">Units</h3><p className="text-sm text-ink-600">Distance and speed display.</p></div>
          <Select value={units} onChange={(event) => setUnits(event.target.value)}><option value="km">Kilometres</option><option value="mi">Miles</option></Select>
        </div>
        <div className="flex items-center justify-between gap-4 p-4">
          <div><h3 className="font-medium">Default map layer</h3><p className="text-sm text-ink-600">Layer used when opening the live monitor.</p></div>
          <Select value={layer} onChange={(event) => setLayer(event.target.value)}><option value="plain">Plain</option><option value="terrain">Terrain</option><option value="satellite">Satellite</option></Select>
        </div>
        <div className="flex items-center justify-between gap-4 p-4">
          <div><h3 className="font-medium">Notifications</h3><p className="text-sm text-ink-600">Show local alert confirmations and warnings.</p></div>
          <label className="flex items-center gap-2 text-sm"><input type="checkbox" checked={notify} onChange={(event) => setNotify(event.target.checked)} /> Enabled</label>
        </div>
      </section>
      <Button variant="primary" onClick={() => pushToast({ title: "Settings saved for this session" })}>Save settings</Button>
    </div>;
};
export {
  Settings
};
