import { ChevronDown } from "lucide-react";
import { useState } from "react";
import { riskCssVar, riskMeta, zoneLabels } from "../../utils/risk";
import { SpeciesIcon } from "../animals/SpeciesIcon";
const MapLegend = () => {
  const [open, setOpen] = useState(false);
  const zoneTypes = Object.entries(zoneLabels);
  const zoneColors = {
    tree_cover: "#327a52", shrubland: "#91a954", grassland: "#d5b75d",
    cultivated_land: "#c58b53", built_up: "#b96055", bare_or_sparse_cover: "#b8a990",
    surface_water: "#4d91b4"
  };
  return <div className={`absolute bottom-4 left-4 z-20 ${open ? "w-64" : "w-28"} rounded-panel border border-line bg-paper/95 p-3 shadow-md`}>
      <button aria-expanded={open} className="flex w-full items-center justify-between text-sm font-medium" onClick={() => setOpen((current) => !current)}>
        Legend
        <ChevronDown className={`h-4 w-4 transition ${open ? "rotate-180" : ""}`} strokeWidth={1.75} />
      </button>
      {open ? <div className="mt-3 space-y-3 text-xs text-ink-600">
          <div>
            <div className="mb-2 text-[11px] font-semibold tracking-[0.08em] text-ink-400">ZONE TYPES</div>
            <div className="grid grid-cols-2 gap-2">
            {zoneTypes.map(([type, label]) => <div key={type} className="flex items-center gap-2">
                <span
    className="h-3 w-5 rounded-[3px] border"
                style={{ background: `color-mix(in srgb, ${zoneColors[type] ?? "#788b7b"} 42%, transparent)`, borderColor: zoneColors[type] ?? "#788b7b" }}
  />
                {label}
              </div>)}
            </div>
            <div className="mt-3 flex items-center gap-2 border-t border-line pt-3"><span className="h-0.5 w-6 rounded bg-[#214b35] ring-2 ring-[#f7f6ef]" />Thick outline · study region</div>
            <p className="mt-1 text-[10px] leading-snug">Land-cover colors follow mapped class shapes inside each region.</p>
          </div>
          <div className="border-t border-line pt-3">
            <div className="mb-2 text-[11px] font-semibold tracking-[0.08em] text-ink-400">SCENARIO STATUS</div>
            <div className="grid grid-cols-2 gap-2">
              {Object.entries(riskMeta).filter(([key]) => key !== "critical" && key !== "info").map(([key, item]) => <div key={key} className="flex items-center gap-2">
                <span className="h-2.5 w-2.5 rounded-full" style={{ background: `var(${riskCssVar(key)})` }} />{item.label}
              </div>)}
            </div>
            <p className="mt-2 text-[10px] leading-snug">Illustrative monitoring labels; not official hazard ratings.</p>
          </div>
          <div className="border-t border-line pt-3">
            <div className="mb-2 text-[11px] font-semibold tracking-[0.08em] text-ink-400">ANIMALS</div>
            <div className="flex items-center gap-4">
            <span className="flex items-center gap-1"><SpeciesIcon species="elephant" className="h-4 w-4" /> Elephant</span>
            <span className="flex items-center gap-1"><SpeciesIcon species="tiger" className="h-4 w-4" /> Tiger</span>
            <span className="flex items-center gap-1"><SpeciesIcon species="deer" className="h-4 w-4" /> Deer</span>
            </div>
          </div>
          <div className="border-t border-line pt-3">
            <div className="mb-2 text-[11px] font-semibold tracking-[0.08em] text-ink-400">STATUS</div>
            <div className="space-y-1">
              <div className="flex items-center gap-2"><span className="h-2 w-2 rounded-full bg-[color:var(--risk-safe)]" /> Active</div>
              <div className="flex items-center gap-2"><span className="h-2 w-2 rounded-full bg-ink-400" /> Idle</div>
              <div className="flex items-center gap-2"><span className="h-2 w-2 rounded-full border border-dashed border-ink-400" /> Offline</div>
              <div className="flex items-center gap-2"><span className="h-2 w-2 rounded-full bg-[color:var(--risk-medium)]" /> Low battery</div>
            </div>
          </div>
        </div> : null}
    </div>;
};
export {
  MapLegend
};
