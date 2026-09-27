const formatTime = (iso) => new Intl.DateTimeFormat("en-IN", {
  hour: "2-digit",
  minute: "2-digit",
  day: "2-digit",
  month: "short"
}).format(new Date(iso));
const formatRelative = (iso) => {
  const diff = Date.now() - new Date(iso).getTime();
  const minutes = Math.max(1, Math.round(diff / 6e4));
  if (minutes < 60) return `${minutes} min ago`;
  const hours = Math.round(minutes / 60);
  return `${hours} hr ago`;
};
const formatCoordinate = (value) => value.toFixed(6);
const titleCase = (value) => value.split("-").map((part) => part.charAt(0).toUpperCase() + part.slice(1)).join(" ");
const directionLabel = (degrees) => {
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
