const Button = ({ variant = "secondary", icon, children, className = "", ...props }) => {
  const styles = {
    primary: "bg-forest-700 text-paper hover:bg-forest-600 border-forest-700",
    secondary: "bg-paper text-ink-900 hover:bg-moss-100 border-line",
    ghost: "bg-transparent text-ink-600 hover:bg-moss-100 border-transparent",
    danger: "bg-[color:var(--risk-critical)] text-paper border-[color:var(--risk-critical)]"
  };
  return <button
    className={`inline-flex min-h-9 items-center justify-center gap-2 rounded-control border px-3 py-2 text-sm font-medium transition duration-150 disabled:opacity-50 ${styles[variant]} ${className}`}
    {...props}
  >
      {icon}
      {children}
    </button>;
};
export {
  Button
};
