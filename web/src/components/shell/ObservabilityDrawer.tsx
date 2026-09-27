import { useCallback, useEffect, useState } from "react";
import { api, apiText, getLastRequest, subscribeLastRequest } from "../../api/client";
import { useDecisionStream, type StreamEvent } from "../../api/sse";
import type { DecisionEvent } from "../../api/types";
import { parsePrometheus } from "../../lib/prometheus";
import { milliseconds } from "../../lib/format";

interface Props {
  open: boolean;
  onClose: () => void;
}

/** Slide-over rendering requests, decisions, and Prometheus metrics while open. */
export function ObservabilityDrawer({ open, onClose }: Props) {
  if (!open) return null;
  return <OpenDrawer onClose={onClose} />;
}

/** Active drawer content, separated so its stream only exists while visible. */
function OpenDrawer({ onClose }: Pick<Props, "onClose">) {
  const [decisions, setDecisions] = useState<DecisionEvent[]>([]);
  const [lastRequest, setLastRequest] = useState(getLastRequest());
  const [metrics, setMetrics] = useState("");
  const [metricsError, setMetricsError] = useState<string | null>(null);
  const [showRaw, setShowRaw] = useState(false);
  const onEvent = useCallback((event: StreamEvent) => {
    if (event.kind !== "decision") return;
    setDecisions((current) => [event.data, ...current].slice(0, 50));
  }, []);
  useDecisionStream(onEvent);

  useEffect(() => subscribeLastRequest(setLastRequest), []);
  useEffect(() => {
    const closeOnEscape = (event: KeyboardEvent) => {
      if (event.key === "Escape") onClose();
    };
    window.addEventListener("keydown", closeOnEscape);
    return () => window.removeEventListener("keydown", closeOnEscape);
  }, [onClose]);
  useEffect(() => {
    let active = true;
    void api<DecisionEvent[]>("/api/v1/demo/decisions?limit=50")
      .then((items) => {
        if (active) {
          setDecisions((current) => mergeDecisions(current, items));
        }
      })
      .catch(() => {
        if (active) setDecisions([]);
      });
    return () => {
      active = false;
    };
  }, []);
  useEffect(() => {
    let active = true;
    const loadMetrics = () => {
      void apiText("/api/v1/metrics")
        .then((text) => {
          if (!active) return;
          setMetrics(text);
          setMetricsError(null);
        })
        .catch((error: unknown) => {
          if (active) {
            setMetricsError(error instanceof Error ? error.message : "Metrics unavailable");
          }
        });
    };
    loadMetrics();
    const timer = window.setInterval(loadMetrics, 5_000);
    return () => {
      active = false;
      window.clearInterval(timer);
    };
  }, []);
  const samples = parsePrometheus(metrics);
  const decisionMetrics = samples.filter((sample) => sample.name === "jev_fhir_decisions_total");
  const requestMetrics = samples.filter((sample) => sample.name === "jev_fhir_http_requests_total");
  return (
    <aside aria-label="Observability drawer" className="observability-drawer">
      <div className="drawer-heading">
        <h2>Observability</h2>
        <button type="button" onClick={onClose}>
          Close
        </button>
      </div>
      <section>
        <h3>Last request</h3>
        <p>Path: {lastRequest?.path ?? "none"}</p>
        <p data-testid="last-request-id">
          Request id: {lastRequest?.requestId ?? "none"}
        </p>
        <p data-testid="last-request-duration">
          Duration: {lastRequest?.durationMs === null || lastRequest === null
            ? "none"
            : milliseconds(lastRequest.durationMs)}
        </p>
      </section>
      <section>
        <h3>Decisions</h3>
        <pre className="decision-log">
          {decisions.map((decision) => JSON.stringify(decision)).join("\n")}
        </pre>
      </section>
      <section>
        <div className="drawer-heading">
          <h3>Metrics</h3>
          <button type="button" onClick={() => setShowRaw((value) => !value)}>
            Show raw
          </button>
        </div>
        {metricsError && <p className="metrics-error">{metricsError}</p>}
        {decisionMetrics.length === 0 ? (
          <p>No decision metrics yet: demo calls don't increment jev_fhir_decisions_total.</p>
        ) : (
          <MetricsTable
            title="Decisions"
            headers={["module", "decision", "count"]}
            rows={decisionMetrics.map((item) => [
              item.labels.module,
              item.labels.decision,
              item.value,
            ])}
          />
        )}
        <MetricsTable
          title="HTTP requests"
          headers={["endpoint", "method", "status", "count"]}
          rows={requestMetrics.map((item) => [
            item.labels.endpoint,
            item.labels.method,
            item.labels.status,
            item.value,
          ])}
        />
        {showRaw && (
          <pre data-testid="raw-metrics" className="metrics-raw">
            {metrics}
          </pre>
        )}
      </section>
    </aside>
  );
}

/** Compact metric table used for each selected Prometheus family. */
function MetricsTable({ title, headers, rows }: {
  title: string;
  headers: string[];
  rows: Array<Array<string | number | undefined>>;
}) {
  return (
    <table aria-label={`${title} metrics`} className="metrics-table">
      <thead>
        <tr>{headers.map((header) => <th key={header}>{header}</th>)}</tr>
      </thead>
      <tbody>
        {rows.map((row, index) => (
          <tr key={`${title}-${index}`}>
            {row.map((value, cell) => <td key={`${index}-${cell}`}>{value ?? ""}</td>)}
          </tr>
        ))}
      </tbody>
    </table>
  );
}

/** Combine replayed and live decisions by descending sequence without duplicates. */
function mergeDecisions(
  current: DecisionEvent[],
  fetched: DecisionEvent[],
): DecisionEvent[] {
  const merged = new Map<number, DecisionEvent>();
  [...current, ...fetched].forEach((decision) => merged.set(decision.seq, decision));
  return [...merged.values()].sort((left, right) => right.seq - left.seq).slice(0, 50);
}
