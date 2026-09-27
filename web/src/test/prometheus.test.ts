import { describe, expect, it } from "vitest";
import captured from "./fixtures/metrics.txt?raw";
import { parsePrometheus } from "../lib/prometheus";

describe("parsePrometheus", () => {
  it("parsePrometheus on a captured metrics sample.", () => {
    expect(parsePrometheus(captured)).toContainEqual({
      name: "jev_fhir_http_requests_total",
      labels: { endpoint: "/compare/{module}", method: "POST", status: "200" },
      value: 1,
    });
    const edgeCases = [
      "# HELP ignored",
      "# TYPE ignored",
      "plain_metric 3",
      'edge{a="x,y=z { }",q="\\"",s="a\\\\b\\nc"} +Inf 123',
      "negative -Inf",
      "nan NaN",
      "timestamped 1e-05 123456",
    ].join("\n");
    expect(parsePrometheus(edgeCases)).toEqual([
      { name: "plain_metric", labels: {}, value: 3 },
      { name: "edge", labels: { a: "x,y=z { }", q: '"', s: "a\\b\nc" }, value: Infinity },
      { name: "negative", labels: {}, value: -Infinity },
      { name: "nan", labels: {}, value: Number.NaN },
      { name: "timestamped", labels: {}, value: 0.00001 },
    ]);
  });
});
