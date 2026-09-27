import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { ErrorCard } from "../components/shell/ErrorCard";
import { ModeBadge } from "../components/shell/ModeBadge";
describe("ErrorCard", () => {
  it("shows the request id", () => {
    render(
      <ErrorCard
        error={{
          error: "bad",
          detail: "detail",
          request_id: "req-7",
          timestamp: "",
        }}
      />,
    );
    expect(screen.getByText("req-7")).toBeVisible();
  });
});
describe("ModeBadge", () => {
  it("renders MOCK with its exact tooltip", async () => {
    vi.stubGlobal(
      "fetch",
      vi
        .fn()
        .mockResolvedValue(
          new Response(
            JSON.stringify({
              status: "ok",
              jev_client: "mock",
              jev_model: null,
              version: "1",
            }),
            { headers: { "X-Request-Id": "r" } },
          ),
        ),
    );
    render(
      <QueryClientProvider client={new QueryClient()}>
        <ModeBadge />
      </QueryClientProvider>,
    );
    expect(
      await screen.findByTitle(
        "Deterministic offline client — decisions are rule-derived, latency is simulated.",
      ),
    ).toHaveTextContent("MOCK");
  });
  it("renders LIVE · jev-latest", async () => {
    vi.stubGlobal(
      "fetch",
      vi
        .fn()
        .mockResolvedValue(
          new Response(
            JSON.stringify({
              status: "ok",
              jev_client: "live",
              jev_model: "jev-latest",
              version: "1",
            }),
          ),
        ),
    );
    render(
      <QueryClientProvider client={new QueryClient()}>
        <ModeBadge />
      </QueryClientProvider>,
    );
    expect(await screen.findByText(/LIVE · jev-latest/)).toBeVisible();
  });
});
