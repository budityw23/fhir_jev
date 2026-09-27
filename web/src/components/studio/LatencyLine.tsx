import { milliseconds } from "../../lib/format";

export interface LatencyLineProps { jevMs: number; e2eMs: number | null; mock: boolean; }

/** Report primitive and whole-request timing without overstating mock latency. */
export function LatencyLine({ jevMs, e2eMs, mock }: LatencyLineProps) {
  const endToEnd = e2eMs === null ? "unavailable" : milliseconds(e2eMs);
  return (
    <p className="latency-line">
      Jev {milliseconds(jevMs)}{mock ? " (simulated)" : ""} · end-to-end {endToEnd}
    </p>
  );
}
