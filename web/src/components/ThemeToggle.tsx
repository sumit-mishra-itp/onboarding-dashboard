import { useState } from "react";
import { flushSync } from "react-dom";

type Theme = "light" | "dark";
const current = (): Theme => (document.documentElement.dataset.theme === "light" ? "light" : "dark");

/** Light/dark switch. public/theme-init.js picks the first theme (saved choice, else the system setting). */
export default function ThemeToggle() {
  const [theme, setTheme] = useState<Theme>(current);
  const next: Theme = theme === "dark" ? "light" : "dark";

  const flip = (e: React.MouseEvent<HTMLButtonElement>) => {
    const apply = () => {
      document.documentElement.dataset.theme = next;
      try { localStorage.setItem("theme", next); } catch { /* private mode: choice lasts this visit only */ }
      flushSync(() => setTheme(next));
    };
    const reduced = matchMedia("(prefers-reduced-motion: reduce)").matches;
    if (reduced || !("startViewTransition" in document)) return apply();
    // The new theme grows out of the button as a circle (see ::view-transition-new in styles.css).
    const r = e.currentTarget.getBoundingClientRect();
    document.documentElement.style.setProperty("--vt-x", `${r.left + r.width / 2}px`);
    document.documentElement.style.setProperty("--vt-y", `${r.top + r.height / 2}px`);
    document.startViewTransition(apply);
  };

  return (
    <button type="button" className="theme-toggle" onClick={flip} aria-label={`Switch to ${next} mode`} title={`Switch to ${next} mode`}>
      {theme === "dark" ? (
        <svg width="18" height="18" viewBox="0 0 24 24" aria-hidden="true" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round">
          <circle cx="12" cy="12" r="4.5" />
          <path d="M12 2v2.5M12 19.5V22M2 12h2.5M19.5 12H22M4.9 4.9l1.8 1.8M17.3 17.3l1.8 1.8M4.9 19.1l1.8-1.8M17.3 6.7l1.8-1.8" />
        </svg>
      ) : (
        <svg width="18" height="18" viewBox="0 0 24 24" aria-hidden="true" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinejoin="round">
          <path d="M20.5 14.5A8.5 8.5 0 0 1 9.5 3.5a8.5 8.5 0 1 0 11 11Z" />
        </svg>
      )}
    </button>
  );
}
