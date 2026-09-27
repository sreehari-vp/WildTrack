import { Menu, Search } from "lucide-react";
import { useEffect, useState } from "react";
import { useLocation } from "react-router-dom";
import { NotificationsMenu } from "./NotificationsMenu";
const titles = {
  "/": "Overview",
  "/monitor": "Live monitor",
  "/animals": "Animals",
  "/zones": "Zones",
  "/alerts": "Alerts",
  "/analytics": "Analytics",
  "/settings": "Settings"
};
const TopBar = ({
  onSearch,
  onMenu
}) => {
  const location = useLocation();
  const [isMac, setIsMac] = useState(false);
  const basePath = `/${location.pathname.split("/")[1]}` === "/" ? "/" : `/${location.pathname.split("/")[1]}`;
  const title = titles[basePath] ?? "WildTrack";
  useEffect(() => {
    setIsMac(navigator.platform.toLowerCase().includes("mac"));
  }, []);
  return <header className="flex h-14 items-center justify-between border-b border-line bg-paper px-4">
      <div className="flex items-center gap-3">
        <button className="grid h-9 w-9 place-items-center rounded-control hover:bg-moss-100 lg:hidden" onClick={onMenu} aria-label="Open navigation">
          <Menu className="h-4 w-4" strokeWidth={1.75} />
        </button>
        <div>
          <h1 className="font-display text-xl text-ink-900">{title}</h1>
          {location.pathname !== "/" ? <p className="text-xs text-ink-400">Nilgiri Ridge Wildlife Reserve</p> : null}
        </div>
      </div>
      <div className="flex items-center gap-3">
        <button
    className="hidden h-9 w-72 items-center justify-between rounded-control border border-line bg-sage-50 px-3 text-sm text-ink-400 md:flex"
    onClick={onSearch}
  >
          <span className="flex items-center gap-2">
            <Search className="h-4 w-4" strokeWidth={1.75} />
            Search
          </span>
          <kbd className="font-mono text-xs">{isMac ? "\u2318K" : "Ctrl K"}</kbd>
        </button>
        <NotificationsMenu />
        <div className="hidden items-center gap-2 text-sm text-ink-600 sm:flex">
          <span className="h-2 w-2 rounded-full bg-[color:var(--risk-safe)]" />
          Monitoring active
        </div>
        <button className="grid h-9 w-9 place-items-center rounded-control bg-forest-700 text-sm font-semibold text-paper" aria-label="Ranger menu">
          RS
        </button>
      </div>
    </header>;
};
export {
  TopBar
};
