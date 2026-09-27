import { describe, expect, it, vi } from "vitest";
import { api, subscribeLastRequest } from "../api/client";

describe("api", () => {
  it("throws ApiError with status, parsed body and requestId on non-2xx", async () => {
    vi.stubGlobal(
      "fetch",
      vi
        .fn()
        .mockResolvedValue(
          new Response(
            JSON.stringify({
              error: "bad",
              detail: "no",
              request_id: "body-id",
              timestamp: "now",
            }),
            { status: 422, headers: { "X-Request-Id": "header-id" } },
          ),
        ),
    );
    await expect(api("/bad")).rejects.toMatchObject({
      status: 422,
      requestId: "header-id",
      body: { error: "bad" },
    });
  });
  it("notifies subscribers with request id and duration headers", async () => {
    vi.stubGlobal(
      "fetch",
      vi
        .fn()
        .mockResolvedValue(
          new Response(JSON.stringify({ ok: true }), {
            headers: {
              "X-Request-Id": "req-9",
              "X-Request-Duration-Ms": "12.5",
            },
          }),
        ),
    );
    const callback = vi.fn();
    const unsubscribe = subscribeLastRequest(callback);
    await api("/ok");
    unsubscribe();
    expect(callback).toHaveBeenCalledWith({
      requestId: "req-9",
      durationMs: 12.5,
      path: "/ok",
    });
  });
});
