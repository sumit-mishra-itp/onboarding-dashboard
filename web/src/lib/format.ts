/** Local calendar date as YYYY-MM-DD. toISOString() would give the UTC date (yesterday before 05:30 IST). */
export const today = () => new Date().toLocaleDateString("en-CA");
export const label = (s: string) => s.replace(/_/g, " ").toLowerCase().replace(/^\w/, (c) => c.toUpperCase());
const ROLE_LABELS: Record<string, string> = { ADMIN: "Admin", HR: "HR", MANAGER: "Manager", JOINEE: "Joinee" };
export const roleLabel = (r: string) => ROLE_LABELS[r] ?? label(r);
export const plural = (n: number, word: string) => `${n} ${word}${n === 1 ? "" : "s"}`;
export const initials = (name = "") => name.split(" ").map((w) => w[0]).join("").slice(0, 2);

const dayFmt = new Intl.DateTimeFormat("en-GB", { weekday: "short", day: "numeric", month: "short" });
export const fmtDate = (iso?: string | null) => (iso ? dayFmt.format(new Date(`${iso.slice(0, 10)}T00:00`)) : "");
/** Days since the start date (0 = start day), from ISO date strings. */
export const daysSince = (start: string, day = today()) => Math.round((Date.parse(day) - Date.parse(start)) / 86_400_000);
/** Invite/reset paths come from the API; the browser knows the public origin. */
export const absoluteUrl = (path: string) => `${window.location.origin}${path}`;
