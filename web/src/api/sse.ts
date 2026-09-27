import { useEffect, useRef, useState } from "react";
import type { DecisionEvent, RunEvent } from "./types";

export type StreamEvent =
  | { kind: "decision"; seq: number; data: DecisionEvent }
  | { kind: "run"; seq: number; data: RunEvent };

/** Subscribe once to the decision feed while always calling the latest event handler. */
export function useDecisionStream(onEvent: (event: StreamEvent) => void): {
  connected: boolean;
} {
  const callback = useRef(onEvent);
  const [connected, setConnected] = useState(false);
  useEffect(() => {
    callback.current = onEvent;
  }, [onEvent]);

  useEffect(() => {
    const source = new EventSource("/api/v1/demo/decisions/stream");
    const receive =
      (kind: StreamEvent["kind"]) => (event: MessageEvent<string>) => {
        callback.current({
          kind,
          seq: Number(event.lastEventId),
          data: JSON.parse(event.data) as DecisionEvent & RunEvent,
        } as StreamEvent);
      };
    source.addEventListener("decision", receive("decision"));
    source.addEventListener("run", receive("run"));
    source.onopen = () => setConnected(true);
    source.onerror = () => setConnected(false);
    return () => source.close();
  }, []);
  return { connected };
}
