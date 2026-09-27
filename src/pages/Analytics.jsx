import { AnalyticsCharts } from "../components/analytics/Charts";
import { KpiRow } from "../components/analytics/KpiRow";
import { useAnalytics } from "../hooks/useAnalytics";
import { DataState } from "./PageState";
const Analytics = () => {
  const analytics = useAnalytics();
  if (analytics.loading || analytics.error || !analytics.data) {
    return <div className="p-6"><DataState loading={analytics.loading} error={analytics.error} onRetry={analytics.retry} /></div>;
  }
  return <div className="space-y-5 p-6">
      <div><h2 className="font-display text-2xl">Analytics</h2><p className="mt-1 text-sm text-ink-600">A restrained operating snapshot for the current patrol day.</p></div>
      <KpiRow metrics={analytics.data.metrics} />
      <AnalyticsCharts analytics={analytics.data} />
    </div>;
};
export {
  Analytics
};
