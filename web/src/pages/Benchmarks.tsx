import { useEffect } from "react";
import { useQueries } from "@tanstack/react-query";
import { useSearchParams } from "react-router-dom";
import { ApiError } from "../api/client";
import { api } from "../api/client";
import type { BenchmarkReport } from "../api/benchmarks";
import { useBenchmark, useBenchmarks } from "../api/queries";
import {
  AccuracyTable,
  BreakdownTable,
  CalibrationChart,
  DisagreementList,
  LatencyPanel,
  LiveVsMock,
  LiveMeta,
  MockDisclaimer,
  NotifiablePRF,
  ReportSelector,
  UnapprovedBanner,
} from "../components/benchmarks/BenchmarkParts";
import { ErrorCard } from "../components/shell/ErrorCard";

/** Present benchmark evidence and links back to the fixture-level Studio evidence. */
export function Benchmarks() {
  const [search, setSearch] = useSearchParams();
  const summaries = useBenchmarks();
  const selected = search.get("report") ?? summaries.data?.[0]?.name ?? null;
  useEffect(() => {
    if (selected && !search.get("report"))
      setSearch({ report: selected }, { replace: true });
  }, [search, selected, setSearch]);
  const report = useBenchmark(selected);
  const reports = useQueries({
    queries: (summaries.data ?? []).map((summary) => ({
      queryKey: ["benchmark", summary.name],
      queryFn: () =>
        api<BenchmarkReport>(`/api/v1/demo/benchmarks/${summary.name}`),
    })),
  });
  if (summaries.error instanceof ApiError) {
    return (
      <main>
        <h2>Benchmarks</h2>
        <ErrorCard error={summaries.error.body} />
      </main>
    );
  }
  if (summaries.data?.length === 0)
    return (
      <main>
        <h2>Benchmarks</h2>
        <p>no report yet</p>
      </main>
    );
  if (!selected || !summaries.data) {
    return (
      <main>
        <h2>Benchmarks</h2>
        <p>Loading reports…</p>
      </main>
    );
  }
  if (report.error instanceof ApiError) {
    return (
      <main>
        <h2>Benchmarks</h2>
        <ErrorCard error={report.error.body} />
      </main>
    );
  }
  if (!report.data)
    return (
      <main>
        <h2>Benchmarks</h2>
        <p>Loading report…</p>
      </main>
    );
  return (
    <main className="benchmarks-page">
      <h2>Benchmarks</h2>
      <ReportSelector
        reports={summaries.data}
        selected={selected}
        onSelect={(name) => setSearch({ report: name })}
      />
      <MockDisclaimer report={report.data} />
      <UnapprovedBanner report={report.data} />
      <AccuracyTable report={report.data} />
      <div className="benchmark-grid">
        <LatencyPanel report={report.data} />
        <NotifiablePRF report={report.data} />
        <LiveMeta report={report.data} />
      </div>
      <BreakdownTable report={report.data} />
      <CalibrationChart report={report.data} />
      <DisagreementList report={report.data} />
      <LiveVsMock
        reports={reports.flatMap((item) =>
          item.data === undefined ? [] : [item.data],
        )}
        selected={report.data}
      />
    </main>
  );
}
