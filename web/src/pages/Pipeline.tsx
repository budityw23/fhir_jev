import { useCallback, useEffect, useReducer, useRef, useState } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import { ApiError, api } from "../api/client";
import { useDecisionStream, type StreamEvent } from "../api/sse";
import { useDemoConfig, useHealth } from "../api/queries";
import { RunControls } from "../components/pipeline/RunControls";
import { ErrorCard } from "../components/shell/ErrorCard";
import {
  ConfidenceHistogram,
  LaneBoard,
  LatencySparkline,
  LiveFeed,
  RerunDelta,
  ReviewQueue,
  StatsStrip,
} from "../components/pipeline/PipelineParts";
import { initialPipelineState, pipelineReducer } from "./pipeline/reducer";

/** Live decision pipeline dashboard backed by the replayable SSE stream. */
export function Pipeline() {
  const [state, dispatch] = useReducer(pipelineReducer, initialPipelineState);
  const onEvent = useCallback(
    (event: StreamEvent) => dispatch({ type: "event", event }),
    [],
  );
  const { connected } = useDecisionStream(onEvent);
  const health = useHealth();
  const config = useDemoConfig();
  const [params] = useSearchParams();
  const navigate = useNavigate();
  const started = useRef(false);
  const [autostartError, setAutostartError] = useState<
    import("../api/types").ErrorBody | null
  >(null);
  useEffect(() => {
    if (
      params.get("autostart") !== "1" ||
      !connected ||
      !config.data ||
      started.current
    )
      return;
    started.current = true;
    void api("/api/v1/demo/pipeline/run", {
      method: "POST",
      body: JSON.stringify({
        source: params.get("source") ?? "unit",
        modules: ["quality", "router", "notifiable"],
        rate_per_s: Number(params.get("rate") ?? "4"),
        thresholds: config.data.thresholds,
      }),
    }).catch((error: unknown) => {
      if (error instanceof ApiError) setAutostartError(error.body);
    });
    navigate("/pipeline", { replace: true });
  }, [config.data, connected, navigate, params]);
  return (
    <main className="pipeline-page">
      <RunControls
        current={state.current}
        onReset={() => dispatch({ type: "reset" })}
      />
      <p>Stream: {connected ? "connected" : "disconnected"}</p>
      {autostartError && <ErrorCard error={autostartError} />}
      <RerunDelta previous={state.previous} current={state.current} />
      <StatsStrip state={state} live={health.data?.jev_client === "live"} />
      <LaneBoard state={state} />
      <div className="chart-grid">
        <LatencySparkline values={state.latencies} />
        <ConfidenceHistogram events={state.events} />
      </div>
      <ReviewQueue events={state.events} />
      <LiveFeed events={state.events} />
    </main>
  );
}
