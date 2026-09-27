import type { StreamEvent } from "../../api/sse";
import type { DecisionEvent } from "../../api/types";

export type Lane = DecisionEvent["lane"];
export interface RunSummary {
  runId: string;
  total: number;
  processed: number;
  status: "running" | "finished" | "stopped";
  lanes: Record<Lane, number>;
  routedByCategory: Record<string, number>;
  agreement: { correct: number; judged: number };
  tokens: number;
  errors: number;
}
export interface PipelineState {
  current: RunSummary | null;
  previous: RunSummary | null;
  events: DecisionEvent[];
  latencies: number[];
  confidences: number[];
}
export type Action = { type: "event"; event: StreamEvent } | { type: "reset" };

export const initialPipelineState: PipelineState = {
  current: null,
  previous: null,
  events: [],
  latencies: [],
  confidences: [],
};

function emptyRun(event: Extract<StreamEvent, { kind: "run" }>): RunSummary {
  return {
    runId: event.data.run_id,
    total: event.data.total,
    processed: 0,
    status: "running",
    lanes: { auto_accepted: 0, routed: 0, flagged: 0, review: 0 },
    routedByCategory: {},
    agreement: { correct: 0, judged: 0 },
    tokens: 0,
    errors: 0,
  };
}

/** Reduce SSE events into display-only state for the currently active pipeline run. */
export function pipelineReducer(
  state: PipelineState,
  action: Action,
): PipelineState {
  if (action.type === "reset") return initialPipelineState;
  const event = action.event;
  if (event.kind === "run" && event.data.status === "started") {
    if (state.current?.runId === event.data.run_id) return state;
    return {
      ...initialPipelineState,
      previous: state.current,
      current: emptyRun(event),
    };
  }
  if (state.current === null || event.data.run_id !== state.current.runId)
    return state;
  if (event.kind === "run") {
    if (event.data.status === "started") return state;
    return {
      ...state,
      current: {
        ...state.current,
        status: event.data.status,
        processed: Math.max(state.current.processed, event.data.processed),
      },
    };
  }
  const decision = event.data;
  const routedByCategory = { ...state.current.routedByCategory };
  if (decision.lane === "routed") {
    routedByCategory[decision.decision] =
      (routedByCategory[decision.decision] ?? 0) + 1;
  }
  const judged = decision.ground_truth_match === null ? 0 : 1;
  return {
    current: {
      ...state.current,
      processed: state.current.processed + 1,
      lanes: {
        ...state.current.lanes,
        [decision.lane]: state.current.lanes[decision.lane] + 1,
      },
      routedByCategory,
      agreement: {
        judged: state.current.agreement.judged + judged,
        correct:
          state.current.agreement.correct +
          (decision.ground_truth_match === true ? 1 : 0),
      },
      tokens: state.current.tokens + decision.tokens_used,
      errors: state.current.errors + (decision.error === null ? 0 : 1),
    },
    previous: state.previous,
    events: [decision, ...state.events].slice(0, 500),
    latencies: [...state.latencies, decision.jev_latency_ms].slice(-50),
    confidences: [...state.confidences, decision.confidence],
  };
}
