import { percent } from "../../lib/format";

export interface ProbabilityBarsProps {
  probabilities: Record<string, number>;
  winner: string;
  floor: number;
  overridden: boolean;
}

/** Show all routing probabilities and explain a confidence-floor override. */
export function ProbabilityBars(
  { probabilities, winner, floor, overridden }: ProbabilityBarsProps,
) {
  const confidence = probabilities[winner] ?? 0;
  return (
    <section aria-label="Route probabilities">
      <h4>Route probabilities</h4>
      {Object.entries(probabilities).map(([name, value]) => (
        <div className="probability-row" key={name}>
          <span>{name}{name === winner ? " ✓" : ""}</span>
          <div className="probability-track">
            <i style={{ width: `${value * 100}%` }} />
            <b style={{ left: `${floor * 100}%` }} />
          </div>
          <span>{percent(value)}</span>
        </div>
      ))}
      {overridden && (
        <p className="override-note">
          overridden: confidence {confidence.toFixed(2)} &lt; {floor.toFixed(2)}
        </p>
      )}
    </section>
  );
}
