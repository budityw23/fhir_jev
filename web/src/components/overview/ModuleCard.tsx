import { Link } from "react-router-dom";
import { api } from "../../api/client";
import { useQuery } from "@tanstack/react-query";
import type { BenchmarkSummary } from "../../api/types";
import { milliseconds, percent } from "../../lib/format";

export interface ModuleCardProps {
  module: "quality" | "router" | "notifiable";
  title: string;
  primitive: string;
  reportKey: "quality_scorer" | "bundle_router" | "notifiable_detector";
}

type ModuleMetrics = { jev_accuracy: number; latency: { p95_ms: number } };
type Report = { modules: Record<string, ModuleMetrics> };

/** Render the latest benchmark result for one decision module. */
export function ModuleCard({ module, title, primitive, reportKey }: ModuleCardProps) {
  const summaries = useQuery({
    queryKey: ["benchmark-summaries"],
    queryFn: () => api<BenchmarkSummary[]>("/api/v1/demo/benchmarks"),
  });
  const latest = summaries.data?.[0];
  const report = useQuery({
    queryKey: ["benchmark-report", latest?.name],
    enabled: latest !== undefined,
    queryFn: () => api<Report>(`/api/v1/demo/benchmarks/${latest!.name}`),
  });
  const metrics = report.data?.modules[reportKey];
  return (
    <article className="module-card">
      <h3>{title}</h3>
      <p>Primitive: {primitive}</p>
      {metrics && latest ? (
        <p>
          Jev accuracy {percent(metrics.jev_accuracy)} · p95 {milliseconds(metrics.latency.p95_ms)}
          <br />
          {latest.mode} · {latest.dataset}
        </p>
      ) : <p>no report yet</p>}
      <Link to={`/studio/${module}`}>Open in Studio</Link>
    </article>
  );
}
