import { useState } from "react";
import { Link } from "react-router-dom";
import { AnalyticsCharts } from "../components/analytics/Charts";
import { KpiRow } from "../components/analytics/KpiRow";
import { useAnalytics } from "../hooks/useAnalytics";
import { Button } from "../components/common/Button";
import { Select } from "../components/common/Select";
import { DataState } from "./PageState";

const localDate = (date) => {
  const year = date.getFullYear();
  const month = String(date.getMonth() + 1).padStart(2, "0");
  const day = String(date.getDate()).padStart(2, "0");
  return `${year}-${month}-${day}`;
};

const initialFilters = () => {
  const end = new Date();
  const start = new Date(end);
  start.setDate(start.getDate() - 6);
  return { start: localDate(start), end: localDate(end), species: "" };
};

const Analytics = () => {
  const [filters, setFilters] = useState(initialFilters);
  const [draft, setDraft] = useState(filters);
  const [rangeError, setRangeError] = useState("");
  const analytics = useAnalytics(filters);
  const applyPreset = (days) => {
    const end = new Date();
    const start = new Date(end);
    start.setDate(start.getDate() - days + 1);
    const next = { ...draft, start: localDate(start), end: localDate(end) };
    setDraft(next);
    setRangeError("");
    setFilters(next);
  };
  const applyFilters = (event) => {
    event.preventDefault();
    if (!draft.start || !draft.end || draft.start > draft.end) {
      setRangeError("Choose a valid date range.");
      return;
    }
    const days = (Date.parse(`${draft.end}T00:00:00Z`) - Date.parse(`${draft.start}T00:00:00Z`)) / 86400000 + 1;
    if (days > 366) {
      setRangeError("Choose a range of 366 days or less.");
      return;
    }
    setRangeError("");
    setFilters(draft);
  };
  const filtersForm = <form onSubmit={applyFilters} className="flex flex-wrap items-end gap-3 rounded-panel border border-line bg-paper p-4">
    <label className="grid gap-1 text-xs text-ink-600">From<input aria-label="Analytics start date" className="min-h-9 rounded-control border border-line bg-paper px-3 text-sm text-ink-900" type="date" value={draft.start} onChange={(event) => setDraft({ ...draft, start: event.target.value })} /></label>
    <label className="grid gap-1 text-xs text-ink-600">To<input aria-label="Analytics end date" className="min-h-9 rounded-control border border-line bg-paper px-3 text-sm text-ink-900" type="date" value={draft.end} onChange={(event) => setDraft({ ...draft, end: event.target.value })} /></label>
    <label className="grid gap-1 text-xs text-ink-600">Species<Select value={draft.species} onChange={(event) => setDraft({ ...draft, species: event.target.value })}><option value="">All species</option><option value="elephant">Elephants</option><option value="tiger">Tigers</option><option value="deer">Deer</option></Select></label>
    <Button type="submit" variant="primary">Apply range</Button>
    <div className="flex gap-2">{[7, 30, 90].map((days) => <Button key={days} type="button" onClick={() => applyPreset(days)}>Last {days} days</Button>)}</div>
    {rangeError && <p role="alert" className="w-full text-xs text-[color:var(--risk-critical)]">{rangeError}</p>}
  </form>;
  if (analytics.loading || analytics.error || !analytics.data) {
    return <div className="space-y-5 p-6">
      <h2 className="font-display text-2xl">Analytics</h2>
      {filtersForm}
      <DataState loading={analytics.loading} error={analytics.error} onRetry={analytics.retry} />
    </div>;
  }
  const startLabel = new Date(`${filters.start}T12:00:00`).toLocaleDateString();
  const endLabel = new Date(`${filters.end}T12:00:00`).toLocaleDateString();
  const speciesLabel = { elephant: "Elephants", tiger: "Tigers", deer: "Deer" }[filters.species] ?? "All species";
  return <div className="space-y-5 p-6">
      <div className="flex flex-wrap items-start justify-between gap-3"><div><h2 className="font-display text-2xl">Analytics</h2><p className="mt-1 text-sm text-ink-600">{startLabel} – {endLabel} · {speciesLabel} · {analytics.data.source}</p><p className="mt-1 text-xs text-ink-400">{analytics.data.note}</p></div><Link to="/movement-network" className="rounded-control border border-line bg-paper px-3 py-2 text-sm font-medium text-forest-700 hover:bg-moss-100">Explore movement corridors →</Link></div>
      {filtersForm}
      {analytics.data.speciesActivity.length === 0 && <p className="rounded-control border border-line bg-paper p-3 text-sm text-ink-600">No GPS observations were recorded for this species and date range.</p>}
      <KpiRow metrics={analytics.data.metrics} />
      <AnalyticsCharts analytics={analytics.data} />
    </div>;
};
export {
  Analytics
};
