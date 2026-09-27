import { useEffect, useState } from "react";
import { Sidebar } from "./Sidebar";
import { TopBar } from "./TopBar";
import { CommandPalette } from "./CommandPalette";
const AppShell = ({ children }) => {
  const [collapsed, setCollapsed] = useState(false);
  const [mobileOpen, setMobileOpen] = useState(false);
  const [commandOpen, setCommandOpen] = useState(false);
  useEffect(() => {
    const onKey = (event) => {
      if ((event.metaKey || event.ctrlKey) && event.key.toLowerCase() === "k") {
        event.preventDefault();
        setCommandOpen(true);
      }
      if (event.key === "Escape") {
        setCommandOpen(false);
        setMobileOpen(false);
      }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, []);
  return <div className={`shell-grid ${collapsed ? "sidebar-collapsed" : ""}`}>
      <Sidebar collapsed={collapsed} onToggle={() => setCollapsed((current) => !current)} mobileOpen={mobileOpen} />
      {mobileOpen ? <button
    className="mobile-scrim fixed inset-0 z-40 hidden bg-forest-950/30"
    aria-label="Close navigation"
    onClick={() => setMobileOpen(false)}
  /> : null}
      <div className="min-w-0">
        <TopBar onSearch={() => setCommandOpen(true)} onMenu={() => setMobileOpen(true)} />
        <main className="min-h-[calc(100vh-56px)]">{children}</main>
      </div>
      <CommandPalette open={commandOpen} onClose={() => setCommandOpen(false)} />
    </div>;
};
export {
  AppShell
};
