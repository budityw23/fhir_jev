import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { HealthDot } from "../components/shell/HealthDot";
describe("HealthDot", () => {
  it("shows the retry banner when health fails", async () => {
    const fetch = vi.fn().mockRejectedValue(new Error("offline"));
    vi.stubGlobal("fetch", fetch);
    render(
      <QueryClientProvider
        client={
          new QueryClient({ defaultOptions: { queries: { retry: false } } })
        }
      >
        <HealthDot />
      </QueryClientProvider>,
    );
    const retry = await screen.findByRole("button", {
      name: "Retry connection",
    });
    expect(screen.getByText(/Offline/)).toBeVisible();
    fireEvent.click(retry);
    expect(fetch).toHaveBeenCalled();
  });
});
