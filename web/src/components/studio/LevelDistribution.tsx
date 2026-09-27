import { percent } from "../../lib/format";

export interface LevelDistributionProps { levels: Record<string, number> | null; }

/** Render live Score uncertainty; callers pass null outside live mode. */
export function LevelDistribution({ levels }: LevelDistributionProps) {
  if (levels === null) return null;
  return (
    <section aria-label="Score distribution">
      <h4>Score distribution</h4>
      {Object.entries(levels).map(([level, value]) => (
        <p key={level}>{level}: {percent(value)}</p>
      ))}
    </section>
  );
}
