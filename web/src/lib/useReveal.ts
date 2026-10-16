import { useEffect } from "react";

/** Sections matching `selector` come into focus once, the first time they scroll into view.
 *  State lives in a data attribute React never writes, so re-renders don't replay the animation. */
export function useReveal(selector: string) {
  useEffect(() => {
    if (matchMedia("(prefers-reduced-motion: reduce)").matches || !("IntersectionObserver" in window)) return;
    const io = new IntersectionObserver((entries) => {
      for (const e of entries) {
        if (!e.isIntersecting) continue;
        (e.target as HTMLElement).dataset.reveal = "in";
        io.unobserve(e.target);
      }
    }, { rootMargin: "0px 0px -6% 0px" });
    const scan = () => document.querySelectorAll<HTMLElement>(selector).forEach((el) => {
      if (el.dataset.reveal) return;
      el.dataset.reveal = "pending";
      io.observe(el);
    });
    scan();
    const mo = new MutationObserver(scan); // screens render their sections after data loads
    mo.observe(document.body, { childList: true, subtree: true });
    return () => { io.disconnect(); mo.disconnect(); };
  }, [selector]);
}
