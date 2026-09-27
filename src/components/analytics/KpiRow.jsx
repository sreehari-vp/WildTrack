const KpiRow = ({ metrics }) => <div className="divider-row grid grid-cols-2 rounded-panel border border-line bg-paper md:grid-cols-5">
    {metrics.map((metric) => <div key={metric.key} className="p-4">
        <div className="font-display text-3xl tabular text-ink-900">{metric.value}<span className="ml-1 text-base">{metric.unit}</span></div>
        <div className="mt-1 text-xs text-ink-600">{metric.label}</div>
      </div>)}
  </div>;
export {
  KpiRow
};
