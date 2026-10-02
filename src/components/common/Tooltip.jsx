const Tooltip = ({ label, children }) => <span className="group relative inline-flex">
    {children}
    <span role="tooltip" className="pointer-events-none absolute left-1/2 top-full z-50 mt-2 hidden -translate-x-1/2 whitespace-nowrap rounded-control border border-line bg-paper px-2 py-1 text-xs text-ink-600 shadow-sm group-hover:block group-focus-within:block">
      {label}
    </span>
  </span>;
export {
  Tooltip
};
