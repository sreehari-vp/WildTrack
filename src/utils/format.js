const formatTime = (iso) => !iso || !Number.isFinite(new Date(iso).getTime()) ? "Unknown" : new Intl.DateTimeFormat("en-IN", {
  hour: "2-digit",
  minute: "2-digit",
  day: "2-digit",
  month: "short"
}).format(new Date(iso));
const formatRelative = (iso) => {
  if (!iso || !Number.isFinite(new Date(iso).getTime())) return "Unknown";
  const diff = Date.now() - new Date(iso).getTime();
  const minutes = Math.max(1, Math.round(diff / 6e4));
  if (minutes < 60) return `${minutes} min ago`;
  const hours = Math.round(minutes / 60);
  return `${hours} hr ago`;
};
const formatCoordinate = (value) => Number.isFinite(value) ? value.toFixed(6) : "Unknown";
const titleCase = (value) => value.split("-").map((part) => part.charAt(0).toUpperCase() + part.slice(1)).join(" ");
const directionLabel = (degrees) => {
  if (!Number.isFinite(degrees)) return "Unavailable";
  const labels = ["N", "NE", "E", "SE", "S", "SW", "W", "NW"];
  return labels[Math.round(degrees / 45) % 8];
};
export {
  directionLabel,
  formatCoordinate,
  formatRelative,
  formatTime,
  titleCase
};
