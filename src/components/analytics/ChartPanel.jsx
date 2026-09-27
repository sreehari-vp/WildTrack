const ChartPanel = ({ title, children }) => <section className="rounded-panel border border-line bg-paper p-4">
    <h2 className="mb-4 font-medium text-ink-900">{title}</h2>
    {children}
  </section>;
export {
  ChartPanel
};
