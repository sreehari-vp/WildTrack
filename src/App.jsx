import { Navigate, Route, Routes } from "react-router-dom";
import { AppShell } from "./components/layout/AppShell";
import { ToastViewport } from "./components/common/Toast";
import { ToastProvider } from "./hooks/useToast";
import { Overview } from "./pages/Overview";
import { LiveMonitor } from "./pages/LiveMonitor";
import { Animals } from "./pages/Animals";
import { AnimalDetail } from "./pages/AnimalDetail";
import { Zones } from "./pages/Zones";
import { Alerts } from "./pages/Alerts";
import { Analytics } from "./pages/Analytics";
import { Settings } from "./pages/Settings";
import { MovementHistory } from "./pages/MovementHistory";
const App = () => <ToastProvider>
    <AppShell>
      <Routes>
        <Route path="/" element={<Overview />} />
        <Route path="/monitor" element={<LiveMonitor />} />
        <Route path="/animals" element={<Animals />} />
        <Route path="/animals/:id" element={<AnimalDetail />} />
        <Route path="/zones" element={<Zones />} />
        <Route path="/alerts" element={<Alerts />} />
        <Route path="/alerts/:id" element={<Alerts />} />
        <Route path="/analytics" element={<Analytics />} />
        <Route path="/settings" element={<Settings />} />
        <Route path="/movement-history" element={<MovementHistory />} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </AppShell>
    <ToastViewport />
  </ToastProvider>;
export {
  App
};
