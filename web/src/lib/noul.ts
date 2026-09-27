/** A display-ready interpretation of a Noul P(statement is true) value. */
export interface NoulView {
  answer: boolean;
  pTrue: number;
  confidence: number;
  label: string;
}

/** Convert P(true) into answer, confidence, and an accessible compact label. */
export function noulView(pTrue: number): NoulView {
  const answer = pTrue >= 0.5;
  const confidence = Math.max(pTrue, 1 - pTrue);
  return {
    answer,
    pTrue,
    confidence,
    label: `${answer ? "✓" : "✗"} ${Math.round(confidence * 100)}%`,
  };
}
