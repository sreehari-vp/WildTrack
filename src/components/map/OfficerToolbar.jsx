import { LocateFixed, MapPin, PencilLine, Radius } from "lucide-react";
import { Tooltip } from "../common/Tooltip";
const OfficerToolbar = ({
  activeTool,
  onChange
}) => {
  const tools = [
    { id: "locate", label: "Location", icon: LocateFixed },
    { id: "pin", label: "Pin", icon: MapPin },
    { id: "radius", label: "Radius zone", icon: Radius },
    { id: "draw", label: "Draw zone", icon: PencilLine }
  ];
  return <details className="absolute left-4 top-20 z-20 rounded-panel border border-line bg-paper/95 p-2 shadow-md">
      <summary className="cursor-pointer text-sm">Map tools</summary>
      <div className="mt-2 flex">
      {tools.map((tool) => {
    const Icon = tool.icon;
    return <Tooltip key={tool.id} label={tool.label}>
            <button
      className={`flex h-9 items-center gap-1.5 rounded-control px-2 ${activeTool === tool.id ? "bg-forest-700 text-paper" : "text-ink-600 hover:bg-moss-100"}`}
      aria-label={tool.label}
      onClick={() => onChange(activeTool === tool.id ? null : tool.id)}
    >
              <Icon className="h-4 w-4" strokeWidth={1.75} />
              <span className="hidden text-xs font-medium xl:inline">{tool.label}</span>
            </button>
          </Tooltip>;
  })}
      </div>
    </details>;
};
export {
  OfficerToolbar
};
