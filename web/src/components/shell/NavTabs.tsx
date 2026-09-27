import { NavLink } from "react-router-dom";

const tabs = [
  ["/", "Overview"],
  ["/studio/quality", "Studio"],
  ["/pipeline", "Pipeline"],
  ["/benchmarks", "Benchmarks"],
  ["/playground", "Playground"],
] as const;
/** Main navigation links for the demo screens. */
export function NavTabs() {
  return (
    <nav aria-label="Demo navigation">
      {tabs.map(([to, label]) => (
        <NavLink key={to} end={to === "/"} to={to}>
          {label}
        </NavLink>
      ))}
    </nav>
  );
}
