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
  return (
    <header className="top-bar">
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
