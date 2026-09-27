const Select = ({ className = "", children, ...props }) => <select
  className={`min-h-9 rounded-control border border-line bg-paper px-3 py-2 text-sm text-ink-900 ${className}`}
  {...props}
>
    {children}
  </select>;
export {
  Select
};
