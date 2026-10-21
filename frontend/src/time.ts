const DAYS = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"];
const MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];

export function formatKickoff(iso: string) {
  const d = new Date(iso);
  const h = d.getHours();
  const m = String(d.getMinutes()).padStart(2, "0");
  return `${DAYS[d.getDay()]} ${d.getDate()} ${MONTHS[d.getMonth()]} · ${h % 12 || 12}:${m} ${h < 12 ? "AM" : "PM"}`;
}

export function hasStarted(iso: string | null, now: number) {
  return !!iso && Date.parse(iso) <= now;
}

export function untilLabel(iso: string, now: number) {
  const mins = Math.round((Date.parse(iso) - now) / 60000);
  if (mins < 60) return `Locks in ${Math.max(1, mins)}m`;
  if (mins < 60 * 24) return `Locks in ${Math.floor(mins / 60)}h ${mins % 60}m`;
  return `Locks in ${Math.floor(mins / 1440)}d`;
}
