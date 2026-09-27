import { Link } from "react-router-dom";
import { ArchitectureDiagram } from "../components/overview/ArchitectureDiagram";
import { ModuleCard } from "../components/overview/ModuleCard";

/** Explain the product and link into the first Studio scene. */
export function Overview() {
  return (
    <main>
      <h2>Overview</h2>
      <p>Typed, probabilistic clinical decisions between FHIR data and operational workflows.</p>
      <Link className="button-link" to="/studio/quality">Start demo</Link>
      <ArchitectureDiagram />
      <div className="module-grid">
        <ModuleCard module="quality" title="Quality" primitive="Score" reportKey="quality_scorer" />
        <ModuleCard module="router" title="Router" primitive="Choice" reportKey="bundle_router" />
        <ModuleCard
          module="notifiable"
          title="Notifiable"
          primitive="Noul"
          reportKey="notifiable_detector"
        />
      </div>
    </main>
  );
}
