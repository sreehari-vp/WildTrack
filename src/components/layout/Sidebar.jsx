import { BarChart3, Bell, CircleDotDashed, Cog, Map, Network, PawPrint, Route, Trees } from "lucide-react";
import { NavLink } from "react-router-dom";
const nav = [
  { label: "Overview", path: "/", icon: BarChart3 },
  { label: "Live Map", path: "/monitor", icon: Map },
  { label: "Animals", path: "/animals", icon: PawPrint },
  { label: "Zones", path: "/zones", icon: Trees },
  { label: "Alerts", path: "/alerts", icon: Bell },
  { label: "Analytics", path: "/analytics", icon: CircleDotDashed },
  { label: "History", path: "/movement-history", icon: Route },
  { label: "Network", path: "/movement-network", icon: Network },
  { label: "Settings", path: "/settings", icon: Cog }
];
const Sidebar = () => <nav className="top-navigation" aria-label="Primary navigation">
  <div className="top-navigation__links">
    {nav.map(({ label, path, icon: Icon }) => <NavLink key={path} to={path} end={path === "/"} aria-label={label}
      className={({ isActive }) => `top-nav-link${isActive ? " is-active" : ""}`}>
      <Icon aria-hidden="true" size={17} strokeWidth={1.8} />
      <span>{label}</span>
    </NavLink>)}
  </div>
</nav>;
export { Sidebar };