import { Expand, Layers, Maximize2, Minus, Plus } from "lucide-react";
import { Tooltip } from "../common/Tooltip";
const MapControls = ({
  onZoomIn,
  onZoomOut,
  onFit,
  onFullscreen,
  layerMode,
  setLayerMode,
  zonesVisible,
  setZonesVisible,
  boundaryVisible,
  setBoundaryVisible,
  animalsVisible,
  setAnimalsVisible,
  pathsVisible,
  setPathsVisible,
  pinsVisible,
  setPinsVisible,
  labelsVisible,
  setLabelsVisible
}) => <div className="absolute right-4 top-24 z-20 flex flex-col gap-2">
    <div className="rounded-panel border border-line bg-paper/95 p-1 shadow-md">
      {[
  { label: "Zoom in", icon: Plus, action: onZoomIn },
  { label: "Zoom out", icon: Minus, action: onZoomOut },
  { label: "Fit to forest", icon: Expand, action: onFit },
  { label: "Fullscreen", icon: Maximize2, action: onFullscreen }
].map((item) => {
  const Icon = item.icon;
  return <Tooltip key={item.label} label={item.label}>
            <button className="grid h-9 w-9 place-items-center rounded-control hover:bg-moss-100" aria-label={item.label} onClick={item.action}>
              <Icon className="h-4 w-4" strokeWidth={1.75} />
            </button>
          </Tooltip>;
})}
    </div>
    <div className="w-44 rounded-panel border border-line bg-paper/95 p-2 shadow-md">
      <div className="mb-2 flex items-center gap-2 text-xs font-medium text-ink-600">
        <Layers className="h-3.5 w-3.5" strokeWidth={1.75} />
        Layers
      </div>
      <select className="mb-2 w-full rounded-control border border-line bg-paper px-2 py-1 text-xs" value={layerMode} onChange={(event) => setLayerMode(event.target.value)}>
        <option value="plain">World map</option>
        <option value="terrain">Terrain tone</option>
        <option value="satellite">Low-light map</option>
      </select>
      <label className="flex items-center gap-2 py-1 text-xs text-ink-600">
        <input type="checkbox" checked={boundaryVisible} onChange={(event) => setBoundaryVisible(event.target.checked)} />
        Forest boundary
      </label>
      <label className="flex items-center gap-2 py-1 text-xs text-ink-600">
        <input type="checkbox" checked={zonesVisible} onChange={(event) => setZonesVisible(event.target.checked)} />
        Zones
      </label>
      <label className="flex items-center gap-2 py-1 text-xs text-ink-600">
        <input type="checkbox" checked={animalsVisible} onChange={(event) => setAnimalsVisible(event.target.checked)} />
        Animals
      </label>
      <label className="flex items-center gap-2 py-1 text-xs text-ink-600">
        <input type="checkbox" checked={pathsVisible} onChange={(event) => setPathsVisible(event.target.checked)} />
        Movement paths
      </label>
      <label className="flex items-center gap-2 py-1 text-xs text-ink-600">
        <input type="checkbox" checked={pinsVisible} onChange={(event) => setPinsVisible(event.target.checked)} />
        Pins
      </label>
      <label className="flex items-center gap-2 py-1 text-xs text-ink-600">
        <input type="checkbox" checked={labelsVisible} onChange={(event) => setLabelsVisible(event.target.checked)} />
        Labels
      </label>
    </div>
  </div>;
export {
  MapControls
};
