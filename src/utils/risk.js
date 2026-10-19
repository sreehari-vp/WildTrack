import {
  AlertOctagon,
  AlertTriangle,
  CheckCircle2,
  Eye,
  Info,
  Siren
} from "lucide-react";
const riskMeta = {
  safe: { label: "Calm", className: "text-[color:var(--risk-safe)]", Icon: CheckCircle2 },
  low: { label: "OK", className: "text-[color:var(--risk-safe)]", Icon: CheckCircle2 },
  medium: { label: "Watch", className: "text-[color:var(--risk-medium)]", Icon: Eye },
  high: { label: "Danger", className: "text-[color:var(--risk-high)]", Icon: AlertTriangle },
  critical: { label: "Critical", className: "text-[color:var(--risk-critical)]", Icon: Siren },
  info: { label: "Unrated", className: "text-[color:var(--risk-info)]", Icon: Info }
};
const severityMeta = {
  info: { label: "Info", risk: "info", Icon: Info },
  low: { label: "Low", risk: "safe", Icon: CheckCircle2 },
  medium: { label: "Medium", risk: "medium", Icon: Eye },
  high: { label: "High", risk: "high", Icon: AlertTriangle },
  critical: { label: "Critical", risk: "critical", Icon: AlertOctagon }
};
const zoneLabels = {
  tree_cover: "Tree cover",
  grassland: "Grassland",
  cultivated_land: "Cultivated land",
  built_up: "Built-up",
  bare_or_sparse_cover: "Bare or sparse cover",
  surface_water: "Water or wetland"
};
const zoneCssVar = {
  tree_cover: "--landcover-tree",
  grassland: "--landcover-grass",
  cultivated_land: "--landcover-crop",
  built_up: "--landcover-built",
  bare_or_sparse_cover: "--landcover-bare",
  surface_water: "--landcover-water"
};
const cssVar = (name, fallback) => {
  if (typeof window === "undefined") return fallback;
  const value = getComputedStyle(document.documentElement).getPropertyValue(name).trim();
  return value || fallback;
};
const riskCssVar = (risk) => ({
  safe: "--risk-safe",
  low: "--risk-safe",
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
