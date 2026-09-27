import { Button } from "../common/Button";
import { Input } from "../common/Input";
import { Select } from "../common/Select";
const RadiusPanel = ({
  draft,
  setDraft,
  onCreate,
  onCancel
}) => <div className="absolute left-20 top-36 z-30 w-80 rounded-panel border border-line bg-paper p-3 shadow-md">
    <h3 className="font-medium text-ink-900">Create radius zone</h3>
    <p className="mt-1 text-xs text-ink-600">Preview updates on the map.</p>
    <div className="mt-3 space-y-3">
      <label className="block text-xs text-ink-600">
        Name
        <Input className="mt-1" value={draft.name} onChange={(event) => setDraft({ ...draft, name: event.target.value })} />
      </label>
      <label className="block text-xs text-ink-600">
        Radius: {draft.radius} m
        <input
  className="mt-2 w-full accent-[color:var(--forest-700)]"
  type="range"
  min={50}
  max={5e3}
  step={50}
  value={draft.radius}
  onChange={(event) => setDraft({ ...draft, radius: Number(event.target.value) })}
/>
      </label>
      <div className="grid grid-cols-2 gap-2">
        <label className="block text-xs text-ink-600">
          Zone type
          <Select className="mt-1 w-full" value={draft.type} onChange={(event) => setDraft({ ...draft, type: event.target.value })}>
            <option value="restricted">Restricted</option>
            <option value="safe">Safe</option>
            <option value="buffer">Buffer</option>
            <option value="high-risk">High risk</option>
            <option value="water-source">Water source</option>
            <option value="protected">Protected</option>
          </Select>
        </label>
        <label className="block text-xs text-ink-600">
          Risk
          <Select className="mt-1 w-full" value={draft.risk} onChange={(event) => setDraft({ ...draft, risk: event.target.value })}>
            <option value="medium">Medium</option>
            <option value="safe">Safe</option>
            <option value="high">High</option>
            <option value="critical">Critical</option>
            <option value="info">Info</option>
          </Select>
        </label>
      </div>
      <div className="flex justify-end gap-2">
        <Button variant="ghost" onClick={onCancel}>Cancel</Button>
        <Button variant="primary" onClick={onCreate} disabled={!draft.name.trim()}>Create zone</Button>
      </div>
    </div>
  </div>;
export {
  RadiusPanel
};
