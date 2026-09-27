import { useEffect, useMemo, useState } from "react";
import {
  BarChart,
  Bar,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { useNavigate } from "react-router-dom";
import { LaneChip } from "../studio/LaneChip";
import { milliseconds, percent } from "../../lib/format";
import type { DecisionEvent } from "../../api/types";
import type { PipelineState, RunSummary } from "../../pages/pipeline/reducer";

function useFrame<T>(value: T): T {
  const [shown, setShown] = useState(value);
  useEffect(() => {
    const frame = requestAnimationFrame(() => setShown(value));
    return () => cancelAnimationFrame(frame);
  }, [value]);
  return shown;
}
function percentile(values: number[], fraction: number): number | null {
  if (!values.length) return null;
  return [...values].sort((a, b) => a - b)[
    Math.ceil(values.length * fraction) - 1
  ];
}

/** Display aggregate metrics for the active pipeline run. */
export function StatsStrip({
  state,
  live,
}: {
  state: PipelineState;
  live: boolean;
}) {
  const run = state.current;
  if (!run)
    return (
      <section className="stats-strip" data-testid="stats-strip">
        No active run.
      </section>
    );
  const newest = state.events[0]?.timestamp;
  const throughput = newest
    ? state.events.filter(
        (event) => Date.parse(newest) - Date.parse(event.timestamp) <= 5000,
      ).length / 5
    : 0;
  const p50 = percentile(state.latencies, 0.5);
  const p95 = percentile(state.latencies, 0.95);
  const agreement = run.agreement.judged
    ? percent(run.agreement.correct / run.agreement.judged)
    : "—";
  const cost = (run.tokens * 42) / 1_000_000_000;
  return (
    <section className="stats-strip" data-testid="stats-strip">
      <span>
        Processed{" "}
        <b>
          {run.processed}/{run.total}
        </b>
      </span>
      <span>
        Throughput <b>{throughput.toFixed(1)}/s</b>
      </span>
      <span>
        p50 <b>{p50 === null ? "—" : milliseconds(p50)}</b>
      </span>
      <span>
        p95 <b>{p95 === null ? "—" : milliseconds(p95)}</b>
      </span>
      <span>
        Agreement <b>{agreement}</b>
      </span>
      <span>
        Tokens <b>{run.tokens}</b>
      </span>
      {live && (
        <span data-testid="cost">
          Cost <b>${cost.toFixed(6)}</b>
        </span>
      )}
    </section>
  );
}

/** Show decisions grouped by their backend-assigned lane. */
export function LaneBoard({ state }: { state: PipelineState }) {
  const lanes = ["auto_accepted", "routed", "flagged", "review"] as const;
  const laneLabels = {
    auto_accepted: "✓ auto_accepted", routed: "✓ routed", flagged: "⚑ flagged", review: "⚠ review",
  };
  return (
    <section className="lane-board" data-testid="lane-board">
      {lanes.map((lane) => (
        <article key={lane}>
          <h3>
            <span className={`lane-heading lane-${lane}`}>{laneLabels[lane]}</span>{" "}
            <span data-testid={`lane-count-${lane}`}>
              {state.current?.lanes[lane] ?? 0}
            </span>
          </h3>
          {lane === "routed" &&
            Object.entries(state.current?.routedByCategory ?? {}).map(
              ([name, count]) => (
                <p key={name}>
                  {name}: {count}
                </p>
              ),
            )}
          {state.events
            .filter((event) => event.lane === lane)
            .slice(0, 8)
            .map((event) => (
              <p key={event.seq}>{event.resource_reference}</p>
            ))}
        </article>
      ))}
    </section>
  );
}

/** Render the newest hundred events and link each back to its Studio fixture. */
export function LiveFeed({ events }: { events: DecisionEvent[] }) {
  const navigate = useNavigate();
  return (
    <section>
      <h3>Live feed</h3>
      <table data-testid="live-feed">
        <thead>
          <tr>
            <th>Time</th>
            <th>Ref</th>
            <th>Module</th>
            <th>Decision</th>
            <th>Confidence</th>
            <th>Latency</th>
            <th>Lane</th>
          </tr>
        </thead>
        <tbody>
          {events.slice(0, 100).map((event) => (
            <tr
              key={event.seq}
              tabIndex={0}
              onClick={() =>
                event.fixture_id &&
                navigate(`/studio/${event.module}?fixture=${event.fixture_id}`)
              }
            >
              <td>{new Date(event.timestamp).toLocaleTimeString()}</td>
              <td>{event.resource_reference}</td>
              <td>{event.module}</td>
              <td>{event.decision}</td>
              <td>
                <meter min="0" max="1" value={event.confidence}>
                  {percent(event.confidence)}
                </meter>
              </td>
              <td>{milliseconds(event.jev_latency_ms)}</td>
              <td>
                <LaneChip lane={event.lane} reason={event.lane_reason} />
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </section>
  );
}

/** Plot the rolling Jev latency sample, updating at most once per animation frame. */
export function LatencySparkline({ values }: { values: number[] }) {
  const shown = useFrame(values);
  return (
    <section className="chart">
      <h3>Latency</h3>
      <ResponsiveContainer width="100%" height={140}>
        <LineChart data={shown.map((value, index) => ({ index, value }))}>
          <Line dataKey="value" stroke="#16803c" dot={false} />
          <Tooltip />
        </LineChart>
      </ResponsiveContainer>
    </section>
  );
}

/** Plot confidence in ten buckets, grouped by module, with frame-throttled updates. */
export function ConfidenceHistogram({ events }: { events: DecisionEvent[] }) {
  const shown = useFrame(events);
  const data = useMemo(
    () =>
      Array.from({ length: 10 }, (_, index) => ({
        bucket: (index / 10).toFixed(1),
        quality: 0,
        router: 0,
        notifiable: 0,
      })).map((bucket, index) => {
        shown.forEach((event) => {
          const selected = Math.min(9, Math.floor(event.confidence * 10));
          if (selected === index) bucket[event.module] += 1;
        });
        return bucket;
      }),
    [shown],
  );
  return (
    <section className="chart">
      <h3>Confidence</h3>
      <ResponsiveContainer width="100%" height={140}>
        <BarChart data={data}>
          <XAxis dataKey="bucket" />
          <YAxis />
          <Tooltip />
          <Bar dataKey="quality" stackId="a" fill="#16803c" />
          <Bar dataKey="router" stackId="a" fill="#667085" />
          <Bar dataKey="notifiable" stackId="a" fill="#b42318" />
        </BarChart>
      </ResponsiveContainer>
    </section>
  );
}

/** Present review explanations and client-only simulated reviewer actions. */
export function ReviewQueue({ events }: { events: DecisionEvent[] }) {
  const [actions, setActions] = useState<Record<number, string>>({});
  const [open, setOpen] = useState<number | null>(null);
  return (
    <section data-testid="review-queue">
      <h3>Review queue</h3>
      <p className="review-caption">simulated reviewer</p>
      <div className="review-list">{events
        .filter((event) => event.lane === "review")
        .map((event) => (
          <article key={event.seq} className="review-item">
            <button className="review-toggle"
              type="button"
              onClick={() => setOpen(open === event.seq ? null : event.seq)}
            >
              {event.resource_reference} · {event.module}
            </button>
            {open === event.seq && (
              <p data-testid="review-reason">{event.lane_reason}</p>
            )}
            <button className="review-action"
              type="button"
              onClick={() =>
                setActions({ ...actions, [event.seq]: "accepted" })
              }
            >
              Accept
            </button>
            <button className="review-action"
              type="button"
              onClick={() =>
                setActions({ ...actions, [event.seq]: "overridden" })
              }
            >
              Override
            </button>
            {actions[event.seq] && <span>{actions[event.seq]}</span>}
          </article>
        ))}</div>
    </section>
  );
}

/** Compare review-queue sizes of consecutive runs. */
export function RerunDelta({
  previous,
  current,
}: {
  previous: RunSummary | null;
  current: RunSummary | null;
}) {
  if (!previous || !current) return null;
  const delta = current.lanes.review - previous.lanes.review;
  const sign =
    delta > 0 ? `+${delta}` : delta < 0 ? `−${Math.abs(delta)}` : "±0";
  return (
    <p data-testid="rerun-delta">
      Review queue: {previous.lanes.review} → {current.lanes.review} (Δ {sign})
    </p>
  );
}
