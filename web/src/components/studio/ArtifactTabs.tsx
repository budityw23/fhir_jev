import { useState } from "react";
import { JsonView } from "./JsonView";

export interface ArtifactTabsProps {
  response: unknown;
  flag: Record<string, unknown> | null;
  auditEvent: Record<string, unknown>;
}

/** Switch among returned API artifacts and copy their unmodified JSON. */
export function ArtifactTabs({ response, flag, auditEvent }: ArtifactTabsProps) {
  const labels = flag === null ? ["Response", "AuditEvent"] : ["Response", "Flag", "AuditEvent"];
  const [active, setActive] = useState("Response");
  const value = active === "Flag" ? flag : active === "AuditEvent" ? auditEvent : response;
  const copy = () => void navigator.clipboard?.writeText(JSON.stringify(value, null, 2));
  return (
    <section aria-label="Artifacts">
      <div className="artifact-controls">
        {labels.map((label) => (
          <button aria-pressed={active === label} className="artifact-tab" key={label}
            onClick={() => setActive(label)}>{label}</button>
        ))}
        <button className="artifact-copy" onClick={copy}>copy</button>
      </div>
      <JsonView collapsedDepth={active === "Response" ? 1 : undefined} value={value} />
    </section>
  );
}
