export interface VerdictStripProps {
  verdict: { jev_correct: boolean | null; rule_correct: boolean | null };
  jevDecision: string;
  ruleDecision: string;
  groundTruth: Record<string, unknown> | null;
}

/** Compare Jev and rule choices against a labelled fixture, when one exists. */
export function VerdictStrip(
  { verdict, jevDecision, ruleDecision, groundTruth }: VerdictStripProps,
) {
  if (groundTruth === null) return null;
  return (
    <section aria-label="Verdict">
      <span>Jev {verdict.jev_correct ? "✓" : "✗"}: {jevDecision}</span>
      <span>Rules {verdict.rule_correct ? "✓" : "✗"}: {ruleDecision}</span>
      <span>Ground truth: {expectedDecision(groundTruth)}</span>
    </section>
  );
}

function expectedDecision(groundTruth: Record<string, unknown>): string {
  const keys = ["expected_action", "expected_category", "expected_status"] as const;
  for (const key of keys) {
    const value = groundTruth[key];
    if (typeof value === "string") return value;
  }
  return "unknown";
}
