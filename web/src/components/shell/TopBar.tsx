import { useLayoutEffect, useRef } from "react";
import { HealthDot } from "./HealthDot";
import { ModeBadge } from "./ModeBadge";
import { NavTabs } from "./NavTabs";

/** Persistent shell controls shared by every demo page. */
export function TopBar({
  onObservability,
  observabilityOpen,
}: {
  onObservability: () => void;
  observabilityOpen: boolean;
}) {
  const header = useRef<HTMLElement>(null);
  // Publish the real bar height (it wraps on narrow screens) so the drawer opens below it.
  useLayoutEffect(() => {
    const element = header.current;
    if (!element || typeof ResizeObserver === "undefined") return;
    const root = document.documentElement;
    const observer = new ResizeObserver(() => {
      root.style.setProperty("--top-bar-height", `${element.offsetHeight}px`);
    });
    observer.observe(element);
    return () => observer.disconnect();
  }, []);
  return (
    <header className="top-bar" ref={header}>
      <h1>Jev × FHIR</h1>
      <NavTabs />
      <ModeBadge />
      <HealthDot />
      <span aria-label="Scene stepper placeholder" />
      <button
        type="button"
        aria-label="Observability"
        aria-expanded={observabilityOpen}
        onClick={onObservability}
      >
        Observability
      </button>
    </header>
  );
}
