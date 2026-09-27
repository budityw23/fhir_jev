import { Link } from "react-router-dom";
import type { ReactNode } from "react";
import {
  Legend,
  ReferenceLine,
  ResponsiveContainer,
  Scatter,
  ScatterChart,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import type {
  BenchmarkModule,
  BenchmarkModuleName,
  BenchmarkReport,
  BenchmarkRow,
} from "../../api/benchmarks";
import type { BenchmarkSummary } from "../../api/types";
import { percent } from "../../lib/format";
import { PRD_TARGETS } from "../../lib/prdTargets";

const modules: Array<[BenchmarkModuleName, string, string]> = [
  ["quality_scorer", "Quality", "quality"],
  ["bundle_router", "Router", "router"],
  ["notifiable_detector", "Notifiable", "notifiable"],
];
/** Select a report and retain its name in the route query string. */
export function ReportSelector({
  reports,
  selected,
  onSelect,
}: {
  reports: BenchmarkSummary[];
  selected: string;
  onSelect: (name: string) => void;
}) {
  return (
    <label className="report-selector">
      Report
      <select
        aria-label="Benchmark report"
        value={selected}
        onChange={(event) => onSelect(event.target.value)}
      >
        {reports.map((report) => (
          <option key={report.name} value={report.name}>
            {report.name} · {report.mode === "mock_jev" ? "MOCK" : "LIVE"} ·{" "}
            {report.dataset} · {report.jev_model ?? "no model"}
          </option>
        ))}
      </select>
      {reports.find((report) => report.name === selected) && (
        <span className="report-details">
          <strong
            className={
              reports.find((report) => report.name === selected)?.mode ===
              "mock_jev"
                ? "mode-mock"
                : "mode-live"
            }
          >
            {reports.find((report) => report.name === selected)?.mode ===
            "mock_jev"
              ? "MOCK"
              : "LIVE"}
          </strong>
          {" · "}
          {reports.find((report) => report.name === selected)?.dataset}
          {" · "}
          {reports.find((report) => report.name === selected)?.jev_model ??
            "no model"}
        </span>
      )}
    </label>
  );
}
function pass(module: BenchmarkModuleName, value: BenchmarkModule): boolean {
  if (module === "notifiable_detector") {
    const prf = value.jev_precision_recall_f1;
    return (
      prf !== undefined &&
      prf.recall >= PRD_TARGETS.notifiable_detector.recallMin &&
      prf.precision >= PRD_TARGETS.notifiable_detector.precisionMin
    );
  }
  return value.jev_accuracy >= PRD_TARGETS[module].min;
}
/** Render PRD agreement targets, including a visible fail state. */
export function AccuracyTable({ report }: { report: BenchmarkReport }) {
  return (
    <section className="benchmark-card">
      <h3>Accuracy</h3>
      <table className="benchmark-table">
        <thead>
          <tr>
            <th>Module</th>
            <th>Jev</th>
            <th>Rules</th>
            <th>PRD target</th>
          </tr>
        </thead>
        <tbody>
          {modules.map(([key, label]) => {
            const data = report.modules[key];
            return (
              <tr key={key}>
                <th>{label}</th>
                <LabelGuard report={report} module={key}>
                  <td>{percent(data.jev_accuracy)}</td>
                  <td>{percent(data.rule_accuracy)}</td>
                  <td>
                    <span
                      className={`prd-chip ${pass(key, data) ? "prd-pass" : "prd-fail"}`}
                    >
                      {pass(key, data) ? "PASS" : "FAIL"} ·{" "}
                      {PRD_TARGETS[key].label}
                    </span>
                  </td>
                </LabelGuard>
              </tr>
            );
          })}
        </tbody>
      </table>
    </section>
  );
}
/** Prevent single-point quality labels from being presented as score accuracy. */
export function LabelGuard({
  report,
  module,
  children,
}: {
  report: BenchmarkReport;
  module: BenchmarkModuleName;
  children: ReactNode;
}) {
  if (module !== "quality_scorer" || report.quality_labels_banded === true)
    return children;
  return (
    <>
      <td>labels not suitable for live scoring</td>
      <td>labels not suitable for live scoring</td>
      <td>labels not suitable for live scoring</td>
    </>
  );
}
/** Render breakdowns only where the report supplies full-dataset aggregates. */
export function BreakdownTable({ report }: { report: BenchmarkReport }) {
  if (report.dataset !== "full") return null;
  return (
    <section className="benchmark-card">
      <h3>Breakdown</h3>
      <div className="breakdown-grid">
        {modules.map(([key, label]) => (
          <div className="breakdown-module" key={key}>
            <h4>{label}</h4>
            <div className="breakdown-pairs">
              <Breakdown
                label="Source"
                values={report.modules[key].breakdown?.source ?? {}}
              />
              <Breakdown
                label="Difficulty"
                values={report.modules[key].breakdown?.difficulty ?? {}}
              />
            </div>
          </div>
        ))}
      </div>
    </section>
  );
}
function Breakdown({
  label,
  values,
}: {
  label: string;
  values: Record<
    string,
    { count: number; jev_accuracy: number; rule_accuracy: number }
  >;
}) {
  return (
    <table className="benchmark-table">
      <caption>{label}</caption>
      <thead>
        <tr>
          <th>Group</th>
          <th>Count</th>
          <th>Jev</th>
          <th>Rules</th>
        </tr>
      </thead>
      <tbody>
        {Object.entries(values).map(([key, value]) => (
          <tr key={key}>
            <th>{key}</th>
            <td>{value.count}</td>
            <td>{percent(value.jev_accuracy)}</td>
            <td>{percent(value.rule_accuracy)}</td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}
/** Show latency percentiles against the two product limits. */
export function LatencyPanel({ report }: { report: BenchmarkReport }) {
  return (
    <section className="benchmark-card">
      <h3>Latency</h3>
      <table className="benchmark-table">
        <caption>PRD: p50 ≤ 30 ms · p95 ≤ 100 ms</caption>
        <thead>
          <tr>
            <th>Module</th>
            <th>Mean</th>
            <th>p50</th>
            <th>p95</th>
            <th>PRD</th>
          </tr>
        </thead>
        <tbody>
          {modules.map(([key, label]) => {
            const latency = report.modules[key].latency;
            const ok = latency.p50_ms <= 30 && latency.p95_ms <= 100;
            const value = (number: number) => `${number.toFixed(1)} ms`;
            return (
              <tr key={key}>
                <th>{label}</th>
                <td>{value(latency.mean_ms)}</td>
                <td>{value(latency.p50_ms)}</td>
                <td>{value(latency.p95_ms)}</td>
                <td>
                  <span className={`prd-chip ${ok ? "prd-pass" : "prd-fail"}`}>
                    {ok ? "PASS" : "FAIL"}
                  </span>
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </section>
  );
}
/** Compare calibration to a perfect-confidence reference diagonal. */
export function CalibrationChart({ report }: { report: BenchmarkReport }) {
  const colors = ["#16803c", "#175cd3", "#b42318"];
  return (
    <section className="benchmark-card">
      <h3>Calibration</h3>
      <div className="calibration-chart">
        <ResponsiveContainer>
          <ScatterChart>
            <XAxis
              type="number"
              dataKey="mean_confidence"
              domain={[0, 1]}
              tickFormatter={percent}
              name="Confidence"
            />
            <YAxis
              type="number"
              dataKey="observed_accuracy"
              domain={[0, 1]}
              tickFormatter={percent}
              name="Accuracy"
            />
            <Tooltip formatter={(value) => percent(Number(value))} />
            <Legend />
            <ReferenceLine
              segment={[
                { x: 0, y: 0 },
                { x: 1, y: 1 },
              ]}
              stroke="var(--c-muted)"
            />
            {modules.map(([key, label], index) => (
              <Scatter
                key={key}
                name={label}
                fill={colors[index]}
                isAnimationActive={false}
                data={report.modules[key].confidence_calibration}
              />
            ))}
          </ScatterChart>
        </ResponsiveContainer>
      </div>
    </section>
  );
}
function values(row: BenchmarkRow): [string, string, string] {
  if ("expected_action" in row)
    return [
      row.expected_action ?? "",
      row.jev_action ?? "",
      row.rule_action ?? "",
    ];
  if ("expected_category" in row)
    return [
      row.expected_category ?? "",
      row.jev_category ?? "",
      row.rule_category ?? "",
    ];
  return [
    String(row.expected_notifiable),
    String(row.jev_notifiable),
    String(row.rule_notifiable),
  ];
}
/** Link every Jev/rule disagreement and every both-wrong result back to Studio. */
export function DisagreementList({ report }: { report: BenchmarkReport }) {
  const rows = modules.flatMap(([key, label, studio]) =>
    report.modules[key].rows
      .filter(
        (row) =>
          row.jev_correct !== row.rule_correct ||
          (!row.jev_correct && !row.rule_correct),
      )
      .map((row) => ({ row, label, studio })),
  );
  return (
    <section className="benchmark-card">
      <h3>Where Jev lost / where rules lost</h3>
      {rows.length === 0 ? (
        <p>No disagreements.</p>
      ) : (
        <ul className="disagreement-list">
          {rows.map(({ row, label, studio }) => {
            const [expected, jev, rules] = values(row);
            return (
              <li key={`${label}-${row.fixture}`}>
                <Link
                  to={`/studio/${studio}?fixture=${encodeURIComponent(row.fixture)}`}
                >
                  {label}: {row.fixture}
                </Link>
                <span>
                  {" "}
                  Expected: {expected} · Jev: {jev} · Rules: {rules}
                </span>
              </li>
            );
          })}
        </ul>
      )}
    </section>
  );
}
/** Compare precision, recall, and F1 for notifiable detection. */
export function NotifiablePRF({ report }: { report: BenchmarkReport }) {
  const data = report.modules.notifiable_detector;
  if (!data.jev_precision_recall_f1 || !data.rule_precision_recall_f1)
    return null;
  const rows: Array<
    [string, { precision: number; recall: number; f1: number }]
  > = [
    ["Jev", data.jev_precision_recall_f1],
    ["Rules", data.rule_precision_recall_f1],
  ];
  return (
    <section className="benchmark-card">
      <h3>Notifiable precision / recall / F1</h3>
      <table className="benchmark-table">
        <thead>
          <tr>
            <th>Method</th>
            <th>Precision</th>
            <th>Recall</th>
            <th>F1</th>
          </tr>
        </thead>
        <tbody>
          {rows.map(([name, prf]) => (
            <tr key={name}>
              <th>{name}</th>
              <td>{percent(prf.precision)}</td>
              <td>{percent(prf.recall)}</td>
              <td>{percent(prf.f1)}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </section>
  );
}
/** Explain why a mock report is useful but not a model-quality measure. */
export function MockDisclaimer({ report }: { report: BenchmarkReport }) {
  return report.mode === "mock_jev" ? (
    <aside className="mock-disclaimer">
      Mock decisions mirror rule logic; this report validates the harness, not
      Jev.
    </aside>
  ) : null;
}
/** Give operational metadata for a live benchmark. */
export function LiveMeta({ report }: { report: BenchmarkReport }) {
  if (report.mode !== "live_jev") return null;
  return (
    <section className="benchmark-card">
      <h3>Live run metadata</h3>
      <p>
        Model: {report.jev_model ?? "unknown"} · Run: {report.generated_at} ·
        Total tokens: {report.token_and_cost?.tokens_used ?? 0} · Estimated
        cost: ${report.token_and_cost?.estimated_cost_usd ?? 0}
      </p>
    </section>
  );
}
/** Compare latest mode-specific reports when their datasets agree. */
export function LiveVsMock({
  reports,
  selected,
}: {
  reports: BenchmarkReport[];
  selected: BenchmarkReport;
}) {
  const pair = reports.filter((report) => report.dataset === selected.dataset);
  const live = pair.find((report) => report.mode === "live_jev");
  const mock = pair.find((report) => report.mode === "mock_jev");
  if (!live || !mock) return null;
  return (
    <section className="benchmark-card">
      <h3>Live vs mock</h3>
      <table className="benchmark-table">
        <thead>
          <tr>
            <th>Module</th>
            <th>Mock</th>
            <th>Live</th>
          </tr>
        </thead>
        <tbody>
          {modules.map(([key, label]) => (
            <tr key={key}>
              <th>{label}</th>
              <td>{percent(mock.modules[key].jev_accuracy)}</td>
              <td>{percent(live.modules[key].jev_accuracy)}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </section>
  );
}
/** Warn when source labels have not been approved for one or more modules. */
export function UnapprovedBanner({ report }: { report: BenchmarkReport }) {
  const entries = modules
    .map(
      ([key, label]) =>
        [label, report.modules[key].unapproved_labels ?? 0] as const,
    )
    .filter(([, count]) => count > 0);
  return entries.length ? (
    <aside className="unapproved-banner">
      Unapproved labels:{" "}
      {entries.map(([label, count]) => `${label} ${count}`).join(", ")}
    </aside>
  ) : null;
}
