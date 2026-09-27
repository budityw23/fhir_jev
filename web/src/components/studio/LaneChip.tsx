import type { CompareResponse } from "../../api/types";

export interface LaneChipProps {
  lane: CompareResponse["lane"];
  reason: string;
}

const laneDisplay = {
  auto_accepted: { icon: "✓", label: "auto_accepted", className: "accept" },
  routed: { icon: "✓", label: "routed", className: "accept" },
  flagged: { icon: "⚑", label: "flagged", className: "flag" },
  review: { icon: "⚠", label: "review", className: "review" },
} as const;

/** Show an accessible, colour-safe lane label and the server's decision explanation. */
export function LaneChip({ lane, reason }: LaneChipProps) {
  const display = laneDisplay[lane];
  return (
    <div className="lane-summary">
      <span className={`lane-chip lane-${display.className}`} data-testid="lane">
        {display.icon} {display.label}
      </span>
      <span data-testid="lane-reason">{reason}</span>
    </div>
  );
}
