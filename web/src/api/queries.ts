import { keepPreviousData, useQuery } from "@tanstack/react-query";
import { api } from "./client";
import type {
  CompareRequest,
  CompareResponse,
  DemoConfig,
  DemoModule,
  FixtureEntry,
  Health,
} from "./types";

/** Produce a stable, lightweight hash for query keys containing FHIR JSON. */
function stableHash(value: unknown): string {
  if (Array.isArray(value)) return `[${value.map(stableHash).join(",")}]`;
  if (value !== null && typeof value === "object") {
    const record = value as Record<string, unknown>;
    return `{${Object.keys(record)
      .sort()
      .map((key) => `${JSON.stringify(key)}:${stableHash(record[key])}`)
      .join(",")}}`;
  }
  return JSON.stringify(value);
}

/** Poll service health every ten seconds. */
export function useHealth() {
  return useQuery({
    queryKey: ["health"],
    queryFn: () => api<Health>("/health"),
    refetchInterval: 10_000,
  });
}
/** Read the configured demo defaults. */
export function useDemoConfig() {
  return useQuery({
    queryKey: ["demo-config"],
    queryFn: () => api<DemoConfig>("/api/v1/demo/config"),
  });
}
/** List fixture metadata with optional URL query filters. */
export function useFixtures(filters: Record<string, string | undefined> = {}) {
  const query = new URLSearchParams(
    Object.entries(filters).filter(
      (entry): entry is [string, string] => entry[1] !== undefined,
    ),
  );
  return useQuery({
    queryKey: ["fixtures", filters],
    queryFn: () =>
      api<FixtureEntry[]>(
        `/api/v1/demo/fixtures${query.size ? `?${query}` : ""}`,
      ),
  });
}
/** Load one allow-listed fixture. */
export function useFixture(id: string | null) {
  return useQuery({
    queryKey: ["fixture", id],
    enabled: id !== null,
    queryFn: () => api<Record<string, unknown>>(`/api/v1/demo/fixtures/${id}`),
  });
}
/** Compare a resource while preserving the previous decision during a refresh. */
export function useCompare(module: DemoModule, input: CompareRequest | null) {
  return useQuery({
    queryKey: [
      module,
      input?.fixture_id ?? stableHash(input?.resource ?? {}),
      input?.thresholds,
    ],
    enabled: input !== null,
    placeholderData: keepPreviousData,
    queryFn: () =>
      api<CompareResponse>(`/api/v1/demo/compare/${module}`, {
        method: "POST",
        body: JSON.stringify(input),
      }),
  });
}
