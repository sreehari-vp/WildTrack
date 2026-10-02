import { useEffect, useState } from "react";
import { Sidebar } from "./Sidebar";
import { TopBar } from "./TopBar";
import { CommandPalette } from "./CommandPalette";
const AppShell = ({ children }) => {
  const [commandOpen, setCommandOpen] = useState(false);
  useEffect(() => {
    const onKey = (event) => {
      if ((event.metaKey || event.ctrlKey) && event.key.toLowerCase() === "k") {
        event.preventDefault();
        setCommandOpen(true);
      }
      if (event.key === "Escape") setCommandOpen(false);
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, []);
  return <div className="app-shell">
      <TopBar onSearch={() => setCommandOpen(true)} />
      <Sidebar />
      <main className="app-main">{children}</main>
      <CommandPalette open={commandOpen} onClose={() => setCommandOpen(false)} />
    </div>;
};
export { AppShell };