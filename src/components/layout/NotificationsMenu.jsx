import { Bell } from "lucide-react";
import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { useAlerts } from "../../hooks/useAlerts";
import { SeverityBadge } from "../alerts/SeverityBadge";
const NotificationsMenu = () => {
  const [open, setOpen] = useState(false);
  const navigate = useNavigate();
  const { data: alerts = [] } = useAlerts(5000);
  const openAlerts = alerts.filter((alert) => alert.status !== "resolved");
  const highCount = openAlerts.filter((alert) => alert.severity === "high" || alert.severity === "critical").length;
  const batteryCount = openAlerts.filter((alert) => alert.type === "low_battery").length;
  return <div className="relative">
      <button
    className="relative grid h-9 w-9 place-items-center rounded-control border border-line bg-paper hover:bg-moss-100"
    aria-label="Notifications"
    onClick={() => setOpen((current) => !current)}
  >
        <Bell className="h-4 w-4" strokeWidth={1.75} />
        {openAlerts.length ? <span className="absolute -right-1 -top-1 grid h-5 min-w-5 place-items-center rounded-full bg-[color:var(--risk-critical)] px-1 text-[11px] font-medium text-paper">
            {openAlerts.length}
          </span> : null}
      </button>
      {open ? <div className="absolute right-0 z-50 mt-2 w-80 rounded-panel border border-line bg-paper p-3 shadow-sm">
          <p className="mb-3 text-sm font-medium text-ink-900">
            {highCount} high-risk alerts · {batteryCount} battery warning
          </p>
          <div className="space-y-1">
            {openAlerts.slice(0, 5).map((alert) => <button
    key={alert.id}
    className="w-full rounded-control px-2 py-2 text-left hover:bg-moss-100"
    onClick={() => {
      navigate(`/alerts/${alert.id}`);
      setOpen(false);
    }}
  >
                <div className="flex items-center justify-between gap-2">
                  <span className="truncate text-sm text-ink-900">{alert.title}</span>
                  <SeverityBadge severity={alert.severity} />
                </div>
              </button>)}
          </div>
        </div> : null}
    </div>;
};
export {
  NotificationsMenu
};
