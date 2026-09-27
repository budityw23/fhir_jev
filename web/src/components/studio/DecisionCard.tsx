import { useHealth } from "../../api/queries";
import type { CompareResponse } from "../../api/types";
import { noulView } from "../../lib/noul";
import { DinkesCard } from "./DinkesCard";
import { LaneChip } from "./LaneChip";
import { LevelDistribution } from "./LevelDistribution";
import { NoulMeter } from "./NoulMeter";
import { ProbabilityBars } from "./ProbabilityBars";
import { ScoreGauge } from "./ScoreGauge";

export interface DecisionCardProps {
  data: CompareResponse;
}

/** Choose the visual decision treatment matching a server-selected module. */
export function DecisionCard({ data }: DecisionCardProps) {
  const lane = <LaneChip lane={data.lane} reason={data.lane_reason} />;
  if (data.module === "quality") return <QualityDecision data={data} lane={lane} />;
  if (data.module === "router") return <RouterDecision data={data} lane={lane} />;
  return <NotifiableDecision data={data} lane={lane} />;
}

function QualityDecision({ data, lane }: DecisionCardProps & { lane: React.ReactNode }) {
  const health = useHealth();
  const jev = data.jev as QualityJev;
  const raw = data.jev_raw.find(
    (call) => call.primitive === "score",
  )?.result as ScoreRaw | undefined;
  const nik = jev.nik_confidence === null ? null : noulView(jev.nik_confidence);
  const levels = health.data?.jev_client === "live" ? raw?.level_probabilities ?? null : null;
  return (
    <section className="decision-card">
      {lane}
      <h3>Quality decision</h3>
      <ScoreGauge
        score={jev.score}
        threshold={data.thresholds.quality_threshold}
        confidence={jev.confidence}
      />
      <p data-testid="quality-action">{jev.level} · {jev.action}</p>
      <p>
        {jev.missing_fields.map((field) => (
          <span className="chip" key={field}>{field}</span>
        ))}
      </p>
      <p>
        NIK gate: {jev.nik_valid === null
          ? "○ unavailable"
          : `${jev.nik_valid ? "✓ valid" : "✗ invalid"} ${nik?.label ?? ""}`}
      </p>
      <LevelDistribution levels={levels} />
    </section>
  );
}

type QualityJev = {
  score: number;
  confidence: number;
  level: string;
  action: string;
  missing_fields: string[];
  nik_valid: boolean | null;
  nik_confidence: number | null;
};

type ScoreRaw = { level_probabilities?: Record<string, number> | null };

function RouterDecision({ data, lane }: DecisionCardProps & { lane: React.ReactNode }) {
  const jev = data.jev as { probabilities: Record<string, number> };
  const raw = data.jev_raw[0]?.result as { choice?: string } | undefined;
  return (
    <section className="decision-card">
      {lane}
      <h3>Router decision</h3>
      <ProbabilityBars
        probabilities={jev.probabilities}
        winner={raw?.choice ?? data.jev_decision}
        floor={data.thresholds.route_confidence_minimum}
        overridden={data.override_applied}
      />
    </section>
  );
}

function NotifiableDecision({ data, lane }: DecisionCardProps & { lane: React.ReactNode }) {
  const jev = data.jev as NotifiableJev;
  const view = noulView(jev.probability);
  return (
    <section className="decision-card">
      {lane}
      <h3>Notifiable decision</h3>
      <p className="noul-answer">{view.label} {jev.status}</p>
      <NoulMeter
        pTrue={jev.probability}
        reviewBand={[
          data.thresholds.notifiable_review,
          data.thresholds.notifiable_confirmed,
        ]}
      />
      {data.lane === "flagged" && (
        <DinkesCard disease={jev.condition_display} urgency="mandatory reporting" />
      )}
    </section>
  );
}

type NotifiableJev = {
  probability: number;
  status: string;
  condition_display: string;
};
