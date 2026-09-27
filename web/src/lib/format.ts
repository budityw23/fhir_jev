/** Format a probability for human-readable UI text. */
export function percent(value: number): string {
  return `${Math.round(value * 100)}%`;
}
/** Format milliseconds without implying excessive precision. */
export function milliseconds(value: number): string {
  return `${Math.round(value)} ms`;
}
