import { useState } from "react";
import { ApiError, api } from "../../api/client";
import { useDemoConfig } from "../../api/queries";
import type { ErrorBody, Thresholds } from "../../api/types";
import { ThresholdSliders } from "../studio/ThresholdSliders";
import { ErrorCard } from "../shell/ErrorCard";
import type { RunSummary } from "../../pages/pipeline/reducer";

interface RunResponse {
  run_id: string;
  status: "started";
  total: number;
}
type Source = "all" | "unit" | "hard" | "generated" | "demo";
const moduleLabel = (module: "quality" | "router" | "notifiable"): string =>
  module === "router" ? "Router" : module[0].toUpperCase() + module.slice(1);
/** Send pipeline commands using the configured thresholds as the initial control values. */
export function RunControls({
  current,
  onReset,
}: {
  current: RunSummary | null;
  onReset: () => void;
}) {
  const config = useDemoConfig();
  const [source, setSource] = useState<Source>("unit");
  const [pace, setPace] = useState("max");
  const [thresholds, setThresholds] = useState<Thresholds | null>(null);
  const [error, setError] = useState<ErrorBody | null>(null);
  const effectiveThresholds = thresholds ?? config.data?.thresholds ?? null;
  const start = async () => {
    if (!effectiveThresholds) return;
    setError(null);
    try {
      await api<RunResponse>("/api/v1/demo/pipeline/run", {
        method: "POST",
        body: JSON.stringify({
          source,
          modules: ["quality", "router", "notifiable"],
          rate_per_s: pace === "max" ? null : Number(pace),
          thresholds: effectiveThresholds,
        }),
      });
    } catch (caught) {
      if (caught instanceof ApiError) setError(caught.body);
    }
  };
  const stop = async () => {
    if (!current || current.status !== "running") return;
    try {
      await api(`/api/v1/demo/pipeline/${current.runId}/stop`, {
        method: "POST",
      });
    } catch (caught) {
      if (caught instanceof ApiError) setError(caught.body);
    }
  };
  return (
    <section className="run-controls" data-testid="run-controls">
      <h2>Live Pipeline</h2>
      <label>
        Source{" "}
        <select
          value={source}
          onChange={(event) => setSource(event.target.value as Source)}
        >
          {["all", "unit", "hard", "generated", "demo"].map((item) => (
            <option key={item}>{item}</option>
          ))}
        </select>
      </label>
      <label>
        Pace{" "}
        <select value={pace} onChange={(event) => setPace(event.target.value)}>
          {["1", "4", "10", "max"].map((item) => (
            <option key={item}>{item}</option>
          ))}
        </select>
      </label>
      {effectiveThresholds && (
        <div className="threshold-grid">
          {(["quality", "router", "notifiable"] as const).map((module) => (
            <fieldset key={module} className="threshold-group">
              <legend>{moduleLabel(module)}</legend>
              <ThresholdSliders module={module} value={effectiveThresholds}
                onChange={setThresholds} />
            </fieldset>
          ))}
        </div>
      )}
      <div className="controls-actions">
        <button className="primary-action" type="button" onClick={() => void start()}>
          Start
        </button>
        <button
          type="button"
          disabled={!current || current.status !== "running"}
          onClick={() => void stop()}
        >
          Stop
        </button>
        <button type="button" onClick={onReset}>
          Reset
        </button>
        <span className="status-pill" data-testid="run-status">
          Status: {current?.status ?? "idle"}
        </span>
      </div>
      {error && <ErrorCard error={error} />}
    </section>
  );
}
