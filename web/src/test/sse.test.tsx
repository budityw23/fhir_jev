import { renderHook, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { useDecisionStream } from "../api/sse";

class MockEventSource {
  static latest: MockEventSource | null = null;
  listeners = new Map<string, (event: MessageEvent<string>) => void>();
  onopen: (() => void) | null = null;
  onerror: (() => void) | null = null;
  close = vi.fn();
  constructor(readonly url: string) {
    MockEventSource.latest = this;
  }
  addEventListener(
    kind: string,
    listener: (event: MessageEvent<string>) => void,
  ) {
    this.listeners.set(kind, listener);
  }
}
describe("useDecisionStream", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
    MockEventSource.latest = null;
  });
  it("wires events, connection state, and cleanup", async () => {
    vi.stubGlobal("EventSource", MockEventSource);
    const onEvent = vi.fn();
    const view = renderHook(() => useDecisionStream(onEvent));
    const source = MockEventSource.latest!;
    expect(source.url).toBe("/api/v1/demo/decisions/stream");
    source.onopen?.();
    await waitFor(() => expect(view.result.current.connected).toBe(true));
    source.listeners.get("decision")?.({
      data: JSON.stringify({ module: "quality" }),
      lastEventId: "12",
    } as MessageEvent<string>);
    source.listeners.get("run")?.({
      data: JSON.stringify({ run_id: "x" }),
      lastEventId: "13",
    } as MessageEvent<string>);
    expect(onEvent).toHaveBeenNthCalledWith(1, {
      kind: "decision",
      seq: 12,
      data: { module: "quality" },
    });
    expect(onEvent).toHaveBeenNthCalledWith(2, {
      kind: "run",
      seq: 13,
      data: { run_id: "x" },
    });
    source.onerror?.();
    await waitFor(() => expect(view.result.current.connected).toBe(false));
    view.unmount();
    expect(source.close).toHaveBeenCalledOnce();
  });
});
