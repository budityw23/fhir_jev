/** Animated overview of the FHIR decision flow. */
export function ArchitectureDiagram() {
  const labels = ["FHIR JSON", "Serializer", "Jev", "Decision", "Action"];
  return (
    <section aria-label="FHIR decision architecture" className="architecture-card">
      <svg viewBox="0 0 900 260" role="img" aria-label="FHIR JSON flows through Jev to an action">
        {labels.map((label, index) => (
          <g key={label} transform={`translate(${20 + index * 175} 80)`}>
            <rect width="135" height="58" rx="8" className="architecture-node" />
            <text x="67" y="34" textAnchor="middle">{label}</text>
            {label === "Jev" && (
              <text x="67" y="51" textAnchor="middle" className="svg-muted">
                Choice / Score / Noul
              </text>
            )}
          </g>
        ))}
        {[0, 1, 2, 3].map((index) => (
          <path
            key={index}
            d={`M${155 + index * 175} 109 H${195 + index * 175}`}
            className="architecture-edge"
          />
        ))}
        <path d="M517 138 V202 H695" className="architecture-next" />
        <text x="535" y="225" className="svg-muted">LLM reasoning layer · next</text>
      </svg>
    </section>
  );
}
