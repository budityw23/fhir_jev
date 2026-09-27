import { useCallback, useReducer } from "react";
import { useDecisionStream, type StreamEvent } from "../api/sse";
import { useHealth } from "../api/queries";
import { RunControls } from "../components/pipeline/RunControls";
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
  return (
    <main className="pipeline-page">
      <RunControls
        current={state.current}
        onReset={() => dispatch({ type: "reset" })}
      />
      <p>Stream: {connected ? "connected" : "disconnected"}</p>
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
