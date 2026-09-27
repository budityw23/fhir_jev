import { fireEvent, render, screen } from "@testing-library/react";
import { readFileSync } from "node:fs";
import { describe, expect, it, vi } from "vitest";
import type { BenchmarkReport, BenchmarkModule } from "../api/benchmarks";
import { BreakdownTable, CalibrationChart } from "../components/benchmarks/BenchmarkParts";
import { FixturePicker } from "../components/studio/FixturePicker";
import { SCENES } from "../scenes";
import catalog from "./fixtures/catalog.json";
import runbook from "../../../docs/demo-runbook.md?raw";

const css = readFileSync("src/index.css", "utf8");

vi.mock("../api/queries", () => ({
  useFixtures: () => ({ data: [{
    id: "one", name: "alpha", label: "Alpha", source: "unit", resource_type: "Patient",
    module: "quality", difficulty: "easy", approved: true, ground_truth: {},
  }] }),
}));

describe("D4 polish", () => {
  it("keeps CSS decision tokens, JSON text, and tinted chips at AA contrast", () => {
    for (const [theme, tokens] of Object.entries(cssThemes())) {
      for (const name of ["accept", "review", "flag", "neutral", "mock", "live"] as const) {
        expectRatio(theme, `${name} on bg`, tokens[name], tokens.bg);
        expectRatio(theme, `${name} on surface`, tokens[name], tokens.surface);
      }
      for (const name of ["accept", "review", "flag", "neutral"] as const) {
        const tint = `${name}Tint` as "acceptTint" | "reviewTint" | "flagTint" | "neutralTint";
        expectRatio(theme, `${name} chip`, tokens[name], tokens[tint]);
      }
      for (const name of ["text", "muted"] as const) {
        expectRatio(theme, `${name} on bg`, tokens[name], tokens.bg);
        expectRatio(theme, `${name} on surface`, tokens[name], tokens.surface);
      }
      expectRatio(theme, "JSON key", tokens.jsonKey, tokens.surface);
      expectRatio(theme, "JSON value", tokens.jsonValue, tokens.surface);
    }
  });

  it("shows no fixtures match after a fixture search has no results", () => {
    render(<FixturePicker module="quality" value={null} onChange={vi.fn()} />);
    fireEvent.change(screen.getByLabelText("Search fixtures"), { target: { value: "missing" } });
    expect(screen.getByText("no fixtures match")).toBeVisible();
  });

  it("gives empty benchmark breakdown and calibration sections explanatory text", () => {
    const report = emptyReport();
    render(<><BreakdownTable report={report} /><CalibrationChart report={report} /></>);
    expect(screen.getByText("No breakdown rows in this report.")).toBeVisible();
    expect(screen.getByText("No calibration rows in this report.")).toBeVisible();
  });

  it("keeps every scene fixture and step fixture in the runbook", () => {
    for (const scene of SCENES) {
      for (const fixture of fixturesFor(scene)) {
        expect(runbook).toContain(fixture.split("/").at(-1)!.replace(".json", ""));
      }
    }
    for (const scene of SCENES) {
      for (const fixture of fixturesFor(scene)) {
        expect(catalog.some((entry) => entry.id === fixture)).toBe(true);
      }
    }
  });
});

function emptyReport(): BenchmarkReport {
  const module: BenchmarkModule = {
    fixture_count: 0, jev_accuracy: 0, rule_accuracy: 0,
    latency: { mean_ms: 0, p50_ms: 0, p95_ms: 0 }, confidence_calibration: [],
    breakdown: { source: {}, difficulty: {} }, rows: [],
  };
  return {
    generated_at: "2000-01-01T00:00:00Z", mode: "mock_jev", dataset: "full",
    modules: { quality_scorer: module, bundle_router: module, notifiable_detector: module },
  };
}

type Tokens = Record<string, string>;

function cssThemes(): Record<"light" | "dark", Tokens> {
  const light = css.match(/:root\s*\{([^}]*)\}/)?.[1];
  const dark = css.match(/@media[^{}]*\{\s*:root\s*\{([^}]*)\}/)?.[1];
  if (!light || !dark) throw new Error("Could not parse light and dark CSS token blocks");
  return { light: parseTokens(light), dark: parseTokens(dark) };
}

function parseTokens(block: string): Tokens {
  const tokens: Tokens = {};
  for (const [, name, value] of block.matchAll(/--c-([\w-]+):\s*(#[0-9a-f]{6})/g)) {
    tokens[name.replace(/-([a-z])/g, (_, letter: string) => letter.toUpperCase())] = value;
  }
  return tokens;
}

function expectRatio(theme: string, pair: string, left: string, right: string): void {
  const ratio = contrast(left, right);
  expect(ratio, `${theme} ${pair}: ${ratio.toFixed(2)} (${left} on ${right})`)
    .toBeGreaterThanOrEqual(4.5);
}

function fixturesFor(scene: (typeof SCENES)[number]): string[] {
  return [scene.fixtureId, ...(scene.steps ?? []).map((step) => step.fixtureId)]
    .filter((fixture): fixture is string => fixture !== undefined);
}

function contrast(left: string, right: string): number {
  const luminance = (hex: string): number => {
    const channels = [1, 3, 5].map(
      (index) => Number.parseInt(hex.slice(index, index + 2), 16) / 255,
    );
    const linear = channels.map((channel) => channel <= 0.04045
      ? channel / 12.92 : ((channel + 0.055) / 1.055) ** 2.4);
    return linear[0] * 0.2126 + linear[1] * 0.7152 + linear[2] * 0.0722;
  };
  const [low, high] = [luminance(left), luminance(right)].sort((a, b) => a - b);
  return (high + 0.05) / (low + 0.05);
}
