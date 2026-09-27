import { percent } from "../../lib/format";

export interface ScoreGaugeProps { score: number; threshold: number; confidence: number; }

/** A compact score gauge with an explicit threshold marker. */
export function ScoreGauge({ score, threshold, confidence }: ScoreGaugeProps) {
  const outerTick = arcPoint(threshold, 80);
  const innerTick = arcPoint(threshold, 64);
  return <section aria-label="Quality score" className="score-gauge">
    <svg aria-label={`Quality score ${score} of 100`} viewBox="0 0 200 140">
      <path className="gauge-arc gauge-track" d="M 20 100 A 80 80 0 0 1 180 100" pathLength="100" />
      <path className="gauge-arc gauge-value" data-testid="score-arc"
        d="M 20 100 A 80 80 0 0 1 180 100" pathLength="100"
        strokeDasharray={`${score} 100`} />
      <line className="gauge-threshold" data-testid="threshold-tick" x1={outerTick.x}
        x2={innerTick.x} y1={outerTick.y} y2={innerTick.y} />
      <text className="gauge-score" x="100" y="70">{score}</text>
      <text className="gauge-label" x="100" y="118">threshold {threshold}</text>
      <text className="gauge-label" x="100" y="134">confidence {percent(confidence)}</text>
    </svg>
  </section>;
}

function arcPoint(threshold: number, radius: number): { x: number; y: number } {
  const angle = Math.PI * (1 - threshold / 100);
  return {
    x: 100 + radius * Math.cos(angle),
    y: 100 - radius * Math.sin(angle),
  };
}
