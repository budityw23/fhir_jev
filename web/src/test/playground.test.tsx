import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";
import type { FixtureEntry } from "../api/types";
import { Playground } from "../pages/Playground";
import quality from "./fixtures/compare_quality.json";

vi.mock("@uiw/react-codemirror", () => ({
  default: ({ onChange, value }: { onChange: (value: string) => void; value: string }) => (
    <textarea aria-label="FHIR JSON" onChange={(event) => onChange(event.target.value)}
      value={value} />
  ),
}));

const hooks = vi.hoisted(() => ({
  fixture: { data: { resourceType: "Patient", id: "starting-point" } },
}));

vi.mock("../api/queries", () => ({
  useFixture: () => hooks.fixture,
  useFixtures: () => ({ data: fixtures }),
  useHealth: () => ({ data: { jev_client: "mock" } }),
}));

const fixtures: FixtureEntry[] = [{
  id: "patients/starting-point.json", name: "starting-point", label: "Starting point",
  source: "unit", resource_type: "Patient", module: "quality", difficulty: "easy",
  approved: true, ground_truth: {},
}];

afterEach(() => {
  cleanup();
  vi.restoreAllMocks();
});

describe("Playground", () => {
  it("disables Run and shows the JSON parse error for invalid input", () => {
    render(<Playground />);
    fireEvent.change(screen.getByLabelText("FHIR JSON"), { target: { value: "{" } });
    expect(screen.getByRole("button", { name: "Run" })).toBeDisabled();
    expect(screen.getByRole("alert")).toHaveTextContent(/JSON|Unexpected/);
  });

  it("loads the selected fixture as pretty-printed editor JSON", async () => {
    const user = userEvent.setup();
    render(<Playground />);
    await user.click(screen.getByLabelText("starting-point"));
    await user.click(screen.getByRole("button", { name: "Load fixture as starting point" }));
    expect(screen.getByLabelText("FHIR JSON")).toHaveValue(
      JSON.stringify(hooks.fixture.data, null, 2),
    );
  });

  it("never sends fixture_id, including after loading a fixture starting point", async () => {
    const user = userEvent.setup();
    const fetchMock = vi.spyOn(globalThis, "fetch").mockResolvedValue(jsonResponse(quality));
    render(<Playground />);
    await user.click(screen.getByLabelText("starting-point"));
    await user.click(screen.getByRole("button", { name: "Load fixture as starting point" }));
    await user.click(screen.getByRole("button", { name: "Run" }));
    await waitFor(() => expect(fetchMock).toHaveBeenCalledOnce());
    const [, init] = fetchMock.mock.calls[0];
    expect(JSON.parse(init?.body as string)).toEqual({
      resource: hooks.fixture.data,
      resource_type: "Patient",
    });
  });

  it(
    "renders the decision lane and artifacts without a verdict strip after a successful Run",
    async () => {
      const user = userEvent.setup();
      vi.spyOn(globalThis, "fetch").mockResolvedValue(jsonResponse(quality));
      render(<Playground />);
      await user.click(screen.getByRole("button", { name: "Run" }));
      expect(await screen.findByTestId("lane")).toBeVisible();
      expect(screen.getByText("Quality decision")).toBeVisible();
      expect(screen.getByLabelText("Artifacts")).toBeVisible();
      expect(screen.queryByText(/^Ground truth:/)).not.toBeInTheDocument();
    },
  );

  it("renders an ApiError response with its request id", async () => {
    const user = userEvent.setup();
    vi.spyOn(globalThis, "fetch").mockResolvedValue(jsonResponse({
      error: "validation_error",
      detail: "subject is required",
      request_id: "123e4567-e89b-12d3-a456-426614174000",
      timestamp: "2026-09-27T00:00:00Z",
    }, 422));
    render(<Playground />);
    await user.click(screen.getByRole("button", { name: "Run" }));
    expect(await screen.findByRole("alert")).toHaveTextContent("validation_error");
    expect(screen.getByRole("alert")).toHaveTextContent("123e4567-e89b-12d3-a456-426614174000");
  });
});

function jsonResponse(body: unknown, status = 200): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: {
      "Content-Type": "application/json",
      "X-Request-Id": "123e4567-e89b-12d3-a456-426614174000",
    },
  });
}
