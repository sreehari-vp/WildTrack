import { Badge } from "../common/Badge";
import { riskMeta, severityMeta } from "../../utils/risk";
const SeverityBadge = ({ severity }) => {
  const meta = severityMeta[severity];
  const risk = riskMeta[meta.risk];
  const Icon = meta.Icon;
  return <Badge className={`${risk.className} ${severity === "critical" ? "animate-pulse" : ""}`}>
      <Icon className="h-3.5 w-3.5" strokeWidth={1.75} />
      {meta.label}
    </Badge>;
};
export {
  SeverityBadge
};
