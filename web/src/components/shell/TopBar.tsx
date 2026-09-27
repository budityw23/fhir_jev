import { HealthDot } from "./HealthDot";
import { ModeBadge } from "./ModeBadge";
import { NavTabs } from "./NavTabs";

/** Persistent shell with intentionally empty D3/D4 control slots. */
export function TopBar() {
  return (
    <header className="top-bar">
      <h1>Jev × FHIR</h1>
      <NavTabs />
      <ModeBadge />
      <HealthDot />
      <span aria-label="Scene stepper placeholder" />
      <span aria-label="Observability drawer placeholder" />
    </header>
  );
}
