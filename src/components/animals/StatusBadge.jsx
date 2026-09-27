import { Badge } from "../common/Badge";
import { riskMeta } from "../../utils/risk";
const RiskBadge = ({ risk }) => {
  const meta = riskMeta[risk];
  const Icon = meta.Icon;
  return <Badge className={`${meta.className} bg-paper`}>
      <Icon className="h-3.5 w-3.5" strokeWidth={1.75} />
      {meta.label}
    </Badge>;
};
const StatusBadge = ({ status }) => {
  const label = status.charAt(0).toUpperCase() + status.slice(1);
  return <Badge className="text-ink-600">
      <span
    className={`h-2 w-2 rounded-full ${status === "active" ? "bg-[color:var(--risk-safe)]" : "bg-ink-400"}`}
  />
      {label}
    </Badge>;
};
export {
  RiskBadge,
  StatusBadge
};
