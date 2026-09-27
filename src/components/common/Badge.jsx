const Badge = ({ children, className = "" }) => <span
  className={`inline-flex min-h-6 items-center gap-1 rounded-control border border-line bg-paper px-2 text-xs font-medium ${className}`}
>
    {children}
  </span>;
export {
  Badge
};
