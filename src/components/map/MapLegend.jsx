import { ChevronDown } from "lucide-react";
import { useState } from "react";
import { zoneCssVar, zoneLabels } from "../../utils/risk";
import { SpeciesIcon } from "../animals/SpeciesIcon";
const MapLegend = () => {
  const [open, setOpen] = useState(false);
  const zoneTypes = Object.entries(zoneLabels);
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
    style={{ background: `color-mix(in srgb, var(${zoneCssVar[type]}) 24%, transparent)`, borderColor: `var(${zoneCssVar[type]})` }}
  />
                {label}
              </div>)}
            </div>
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
