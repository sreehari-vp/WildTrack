import { lazy, Suspense } from "react";
import { Navigate, Route, Routes } from "react-router-dom";
import { AppShell } from "./components/layout/AppShell";
import { ToastViewport } from "./components/common/Toast";
import { ToastProvider } from "./hooks/useToast";
import { WildTrackLoader } from "./components/common/WildTrackLoader";
const lazyPage = (loader, name) => lazy(() => loader().then((module) => ({ default: module[name] })));
const Overview = lazyPage(() => import("./pages/Overview"), "Overview");
const LiveMonitor = lazyPage(() => import("./pages/LiveMonitor"), "LiveMonitor");
const Animals = lazyPage(() => import("./pages/Animals"), "Animals");
const AnimalDetail = lazyPage(() => import("./pages/AnimalDetail"), "AnimalDetail");
const Zones = lazyPage(() => import("./pages/Zones"), "Zones");
const Alerts = lazyPage(() => import("./pages/Alerts"), "Alerts");
const Analytics = lazyPage(() => import("./pages/Analytics"), "Analytics");
const Settings = lazyPage(() => import("./pages/Settings"), "Settings");
const MovementHistory = lazyPage(() => import("./pages/MovementHistory"), "MovementHistory");
const MovementNetwork = lazyPage(() => import("./pages/MovementNetwork"), "MovementNetwork");
const App = () => <ToastProvider>
    <AppShell>
      <Suspense fallback={<WildTrackLoader />}>
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
        <Route path="/movement-network" element={<MovementNetwork />} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
      </Suspense>
    </AppShell>
    <ToastViewport />
  </ToastProvider>;
export {
  App
};
