import {
  AlertTriangle,
  BarChart3,
  Bell,
  ChevronLeft,
  CircleDotDashed,
  Cog,
  Map,
  PawPrint,
  Route,
  Trees
} from "lucide-react";
import { NavLink } from "react-router-dom";
import { Tooltip } from "../common/Tooltip";
import { BrandMark } from "./BrandMark";
const nav = [
  { label: "Overview", path: "/", icon: BarChart3 },
  { label: "Live Monitor", path: "/monitor", icon: Map },
  { label: "Animals", path: "/animals", icon: PawPrint },
  { label: "Zones", path: "/zones", icon: Trees },
  { label: "Alerts", path: "/alerts", icon: Bell },
  { label: "Analytics", path: "/analytics", icon: CircleDotDashed },
  { label: "Settings", path: "/settings", icon: Cog },
  { label: "Movement History", path: "/movement-history", icon: Route }
];
const Sidebar = ({
  collapsed,
  onToggle,
  mobileOpen
}) => <aside
  className="app-sidebar flex min-h-screen flex-col bg-forest-950 p-3 text-moss-300"
  data-open={mobileOpen}
>
    <div className="mb-6 flex items-center justify-between px-1 pt-1">
      <BrandMark compact={collapsed} />
      <button
  className="hidden h-9 w-9 place-items-center rounded-control text-moss-300 hover:bg-forest-900 lg:grid"
  onClick={onToggle}
  aria-label={collapsed ? "Expand sidebar" : "Collapse sidebar"}
>
        <ChevronLeft className={`h-4 w-4 transition ${collapsed ? "rotate-180" : ""}`} strokeWidth={1.75} />
      </button>
    </div>
    <nav className="space-y-1">
      {nav.map((item) => {
  const Icon = item.icon;
  const link = <NavLink
    to={item.path}
    className={({ isActive }) => `relative flex min-h-10 items-center gap-3 rounded-control px-3 text-sm font-medium transition hover:bg-forest-900 ${isActive ? "bg-forest-900 text-paper before:absolute before:left-0 before:h-6 before:w-0.5 before:bg-moss-300" : ""} ${collapsed ? "justify-center" : ""}`}
  >
            <Icon className="h-4.5 w-4.5 shrink-0" strokeWidth={1.75} />
            {!collapsed ? <span>{item.label}</span> : null}
          </NavLink>;
  return collapsed ? <Tooltip key={item.path} label={item.label}>
            {link}
          </Tooltip> : <div key={item.path}>{link}</div>;
})}
    </nav>
    <div className="mt-auto rounded-panel border border-moss-300/20 p-3 text-xs text-moss-300/80">
      {collapsed ? <AlertTriangle className="h-4 w-4" strokeWidth={1.75} /> : "Monitoring active across Nilgiri Ridge Wildlife Reserve."}
    </div>
  </aside>;
export {
  Sidebar
};
