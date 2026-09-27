import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { afterEach, describe, expect, it, vi } from "vitest";
import { ObservabilityDrawer } from "../components/shell/ObservabilityDrawer";
import { api } from "../api/client";
import { App } from "../App";
import { Pipeline } from "../pages/Pipeline";

class MockEventSource {
  static latest: MockEventSource | null = null;
  onopen: (() => void) | null = null;
  onerror: (() => void) | null = null;
  listeners = new Map<string, (event: MessageEvent<string>) => void>();
  constructor() {
    MockEventSource.latest = this;
  }
  addEventListener(kind: string, listener: (event: MessageEvent<string>) => void) {
    this.listeners.set(kind, listener);
  }
  close = vi.fn();
}

const metrics = [
  'jev_fhir_decisions_total{module="quality",decision="auto_accept"} 4',
  'jev_fhir_http_requests_total{endpoint="/compare/{module}",method="POST",status="200"} 7',
].join("\n");

describe("ObservabilityDrawer", () => {
  afterEach(() => {
    cleanup();
    vi.unstubAllGlobals();
    vi.useRealTimers();
    MockEventSource.latest = null;
  });
  it("loads decisions, polls only while visible, and renders details", async () => {
    vi.useFakeTimers({ shouldAdvanceTime: true });
    vi.stubGlobal("EventSource", MockEventSource);
    const fetchMock = vi.fn()
      .mockResolvedValueOnce(new Response(JSON.stringify({ ok: true }), {
        headers: { "X-Request-Id": "before-id", "X-Request-Duration-Ms": "8" },
      }))
      .mockResolvedValueOnce(new Response(JSON.stringify([{ seq: 1, module: "quality" }]), {
        headers: { "X-Request-Id": "before-id", "X-Request-Duration-Ms": "8" },
      }))
      .mockImplementation(() => Promise.resolve(new Response(metrics, {
        headers: { "X-Request-Id": "before-id", "X-Request-Duration-Ms": "8" },
      })));
    vi.stubGlobal("fetch", fetchMock);
    await api("/before", { headers: { Accept: "application/json" } }).catch(() => undefined);
    const view = render(<ObservabilityDrawer open onClose={vi.fn()} />);
    await waitFor(() => expect(screen.getByText(/"seq":1/)).toBeInTheDocument());
    expect(screen.getByTestId("last-request-id")).toHaveTextContent("before-id");
    expect(screen.getByRole("table", { name: "Decisions metrics" })).toHaveTextContent("quality");
    expect(
      screen.getByRole("table", { name: "HTTP requests metrics" }),
    ).toHaveTextContent("POST");
    fireEvent.click(screen.getByRole("button", { name: "Show raw" }));
    expect(screen.getByTestId("raw-metrics")).toHaveTextContent("decisions_total");
    await vi.advanceTimersByTimeAsync(5_000);
    expect(fetchMock.mock.calls.length).toBeGreaterThan(3);
    const callsWhileOpen = fetchMock.mock.calls.length;
    view.rerender(<ObservabilityDrawer open={false} onClose={vi.fn()} />);
    await vi.advanceTimersByTimeAsync(10_000);
    expect(fetchMock.mock.calls.length).toBe(callsWhileOpen);
    vi.useRealTimers();
  });
  it("shows request state before drawer fetches and receives later request updates", async () => {
    vi.stubGlobal("EventSource", MockEventSource);
    let resolveDrawer: ((response: Response) => void) | undefined;
    const fetchMock = vi.fn((path: string) => {
      if (path === "/before") return Promise.resolve(response({ ok: true }, "before-id", 4));
      if (path.includes("decisions") || path.includes("metrics")) {
        return new Promise<Response>((resolve) => {
          resolveDrawer = resolve;
        });
      }
      return Promise.resolve(response({ ok: true }, "later-id", 9));
    });
    vi.stubGlobal("fetch", fetchMock);
    await api("/before");
    render(<ObservabilityDrawer open onClose={vi.fn()} />);
    expect(screen.getByTestId("last-request-id")).toHaveTextContent("before-id");
    await api("/later");
    await waitFor(() => {
      expect(screen.getByTestId("last-request-id")).toHaveTextContent("later-id");
    });
    resolveDrawer!(new Response(JSON.stringify([])));
  });
  it("closes from Escape and its Close button", () => {
    vi.stubGlobal("EventSource", MockEventSource);
    vi.stubGlobal("fetch", vi.fn(() => Promise.resolve(new Response(metrics))));
    const onClose = vi.fn();
    render(<ObservabilityDrawer open onClose={onClose} />);
    fireEvent.keyDown(window, { key: "Escape" });
    fireEvent.click(screen.getByRole("button", { name: "Close" }));
    expect(onClose).toHaveBeenCalledTimes(2);
  });
  it("toggles drawer state through the TopBar", async () => {
    vi.stubGlobal("EventSource", MockEventSource);
    vi.stubGlobal("fetch", vi.fn((path: string) => {
      if (path.includes("decisions")) return Promise.resolve(response([], "drawer-id", 1));
      if (path.includes("metrics")) return Promise.resolve(response(metrics, "metrics-id", 2));
      return Promise.resolve(response({
        status: "ok", jev_client: "mock", jev_model: null, version: "1",
      }, "health-id", 1));
    }));
    render(
      <QueryClientProvider client={new QueryClient()}>
        <MemoryRouter><App /></MemoryRouter>
      </QueryClientProvider>,
    );
    const button = screen.getByRole("button", { name: "Observability" });
    fireEvent.click(button);
    expect(screen.getByLabelText("Observability drawer")).toBeVisible();
    expect(button).toHaveAttribute("aria-expanded", "true");
    fireEvent.click(button);
    await waitFor(() => expect(screen.queryByLabelText("Observability drawer")).toBeNull());
    expect(button).toHaveAttribute("aria-expanded", "false");
  });
  it("shows connected then disconnected stream states on Pipeline", async () => {
    vi.stubGlobal("EventSource", MockEventSource);
    vi.stubGlobal("ResizeObserver", class {
      observe() {}
      unobserve() {}
      disconnect() {}
    });
    vi.stubGlobal("fetch", vi.fn(() => Promise.resolve(response({
      status: "ok", jev_client: "mock", jev_model: null, version: "1",
    }, "health-id", 1))));
    render(
      <QueryClientProvider client={new QueryClient()}>
        <MemoryRouter><Pipeline /></MemoryRouter>
      </QueryClientProvider>,
    );
    MockEventSource.latest!.onopen?.();
    await waitFor(() => expect(screen.getByText("Stream: connected")).toBeVisible());
    MockEventSource.latest!.onerror?.();
    await waitFor(() => expect(screen.getByText("Stream: disconnected")).toBeVisible());
  });
  it("keeps a live event that arrives before the decisions request resolves", async () => {
    vi.stubGlobal("EventSource", MockEventSource);
    let resolveDecisions: ((response: Response) => void) | undefined;
    vi.stubGlobal("fetch", vi.fn((path: string) => {
      if (path.includes("decisions")) {
        return new Promise<Response>((resolve) => {
          resolveDecisions = resolve;
        });
      }
      return Promise.resolve(new Response(metrics));
    }));
    render(<ObservabilityDrawer open onClose={vi.fn()} />);
    MockEventSource.latest!.listeners.get("decision")?.({
      data: JSON.stringify({ seq: 9, module: "quality" }),
      lastEventId: "9",
    } as MessageEvent<string>);
    resolveDecisions!(new Response(JSON.stringify([{ seq: 8, module: "router" }])));
    await waitFor(() => expect(screen.getByText(/"seq":9/)).toBeInTheDocument());
    expect(screen.getByText(/"seq":8/)).toBeInTheDocument();
  });
  it("shows an inline metrics error and the empty decision note", async () => {
    vi.stubGlobal("EventSource", MockEventSource);
    vi.stubGlobal("fetch", vi.fn((path: string) => Promise.resolve(
      path.includes("metrics")
        ? new Response("no", { status: 500 })
        : new Response(JSON.stringify([])),
    )));
    render(<ObservabilityDrawer open onClose={vi.fn()} />);
    expect(await screen.findByText(/Metrics request failed/)).toBeVisible();
    expect(screen.getAllByText(/No decision metrics yet/)).not.toHaveLength(0);
  });
});

/** Build a response whose headers verify independent request metadata updates. */
function response(body: unknown, requestId: string, duration: number): Response {
  return new Response(JSON.stringify(body), {
    headers: {
      "X-Request-Id": requestId,
      "X-Request-Duration-Ms": String(duration),
    },
  });
}
