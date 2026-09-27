const Input = ({ className = "", ...props }) => <input
  className={`min-h-9 w-full rounded-control border border-line bg-paper px-3 py-2 text-sm text-ink-900 placeholder:text-ink-400 ${className}`}
  {...props}
/>;
export {
  Input
};
