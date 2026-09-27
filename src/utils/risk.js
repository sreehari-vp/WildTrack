import {
  AlertOctagon,
  AlertTriangle,
  CheckCircle2,
  Eye,
  Info,
  Siren
} from "lucide-react";
const riskMeta = {
  safe: { label: "Safe", className: "text-[color:var(--risk-safe)]", Icon: CheckCircle2 },
  medium: { label: "Medium", className: "text-[color:var(--risk-medium)]", Icon: Eye },
  high: { label: "High", className: "text-[color:var(--risk-high)]", Icon: AlertTriangle },
  critical: { label: "Critical", className: "text-[color:var(--risk-critical)]", Icon: Siren },
  info: { label: "Info", className: "text-[color:var(--risk-info)]", Icon: Info }
};
const severityMeta = {
  info: { label: "Info", risk: "info", Icon: Info },
  low: { label: "Low", risk: "safe", Icon: CheckCircle2 },
  medium: { label: "Medium", risk: "medium", Icon: Eye },
  high: { label: "High", risk: "high", Icon: AlertTriangle },
  critical: { label: "Critical", risk: "critical", Icon: AlertOctagon }
};
const zoneLabels = {
  safe: "Safe",
  buffer: "Buffer",
  restricted: "Restricted",
  "high-risk": "High risk",
  "water-source": "Water source",
  protected: "Protected"
};
const zoneCssVar = {
  safe: "--risk-safe",
  buffer: "--risk-medium",
  restricted: "--risk-high",
  "high-risk": "--risk-critical",
  "water-source": "--risk-info",
  protected: "--zone-protected"
};
const cssVar = (name, fallback) => {
  if (typeof window === "undefined") return fallback;
  const value = getComputedStyle(document.documentElement).getPropertyValue(name).trim();
  return value || fallback;
};
const riskCssVar = (risk) => ({
  safe: "--risk-safe",
  medium: "--risk-medium",
  high: "--risk-high",
  critical: "--risk-critical",
  info: "--risk-info"
})[risk];
export {
  cssVar,
  riskCssVar,
  riskMeta,
  severityMeta,
  zoneCssVar,
  zoneLabels
};
