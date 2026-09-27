import { percent } from "../../lib/format";

export interface ScoreGaugeProps { score: number; threshold: number; confidence: number; }

/** A compact score gauge with an explicit threshold marker. */
export function ScoreGauge({ score, threshold, confidence }: ScoreGaugeProps) {
  return <section aria-label="Quality score" className="score-gauge">
    <strong>{score}/100</strong>
    <span>threshold {threshold}</span>
    <span>confidence {percent(confidence)}</span>
    <div className="gauge-track">
      <i style={{ width: `${score}%` }} />
      <b style={{ left: `${threshold}%` }} />
    </div>
  </section>;
}
