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
const Alerts = lazyPage(() => import("./pages/Alerts"), "Alerts");
const Analytics = lazyPage(() => import("./pages/Analytics"), "Analytics");
const Settings = lazyPage(() => import("./pages/Settings"), "Settings");
const MovementHistory = lazyPage(() => import("./pages/MovementHistory"), "MovementHistory");
const MovementNetwork = lazyPage(() => import("./pages/MovementNetwork"), "MovementNetwork");
const FieldRecords = lazyPage(() => import("./pages/FieldRecords"), "FieldRecords");
const Zones = lazyPage(() => import("./pages/Zones"), "Zones");
const App = () => <ToastProvider>
    <AppShell>
      <Suspense fallback={<WildTrackLoader />}>
      <Routes>
        <Route path="/" element={<FieldRecords defaultLandCover title="Ooty Wildlife Map" description="Eight forest analysis regions, sourced mammal records, and 75 simulated wildlife trackers. Turn on land cover to compare ESA classes within each region." />} />
        <Route path="/overview" element={<Overview />} />
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
        <Route path="/field-records" element={<FieldRecords defaultLandCover />} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
      </Suspense>
    </AppShell>
    <ToastViewport />
  </ToastProvider>;
export {
  App
};
