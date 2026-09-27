import { json } from "@codemirror/lang-json";
import CodeMirror from "@uiw/react-codemirror";
import { useEffect, useMemo, useState } from "react";
import { ApiError, api, subscribeLastRequest } from "../api/client";
import { useFixture, useHealth } from "../api/queries";
import type { CompareRequest, CompareResponse, DemoModule } from "../api/types";
import { ErrorCard } from "../components/shell/ErrorCard";
import { ArtifactTabs } from "../components/studio/ArtifactTabs";
import { DecisionCard } from "../components/studio/DecisionCard";
import { FixturePicker } from "../components/studio/FixturePicker";
import { LatencyLine } from "../components/studio/LatencyLine";

const modules: DemoModule[] = ["quality", "router", "notifiable"];

/** Run freely edited FHIR JSON without associating it with fixture ground truth. */
export function Playground() {
  const [module, setModule] = useState<DemoModule>("quality");
  const [fixtureId, setFixtureId] = useState<string | null>(null);
  const [text, setText] = useState("{}");
  const [result, setResult] = useState<CompareResponse | null>(null);
  const [error, setError] = useState<ApiError | null>(null);
  const [e2eMs, setE2eMs] = useState<number | null>(null);
  const fixture = useFixture(fixtureId);
  const health = useHealth();
  const parsed = useMemo(() => parseJson(text), [text]);

  useEffect(() => subscribeLastRequest((request) => {
    if (request.path.startsWith(`/api/v1/demo/compare/${module}`)) {
      setE2eMs(request.durationMs);
    }
  }), [module]);

  const selectModule = (next: DemoModule): void => {
    setModule(next);
    setFixtureId(null);
    setResult(null);
    setError(null);
  };
  const loadFixture = (): void => {
    if (fixture.data) setText(JSON.stringify(fixture.data, null, 2));
  };
  const run = async (): Promise<void> => {
    if (parsed.error !== null) return;
    setError(null);
    setResult(null);
    try {
      const input = playgroundInput(module, parsed.value);
      const response = await api<CompareResponse>(`/api/v1/demo/compare/${module}`, {
        method: "POST",
        body: JSON.stringify(input),
      });
      setResult(response);
    } catch (caught) {
      if (caught instanceof ApiError) setError(caught);
      else throw caught;
    }
  };

  return (
    <main>
      <h2>Playground</h2>
      <label>
        Module
        <select value={module} onChange={(event) => selectModule(event.target.value as DemoModule)}>
          {modules.map((item) => <option key={item} value={item}>{item}</option>)}
        </select>
      </label>
      <div className="studio-grid">
        <div>
          <FixturePicker module={module} value={fixtureId} onChange={setFixtureId} />
          <button disabled={!fixture.data} onClick={loadFixture} type="button">
            Load fixture as starting point
          </button>
        </div>
        <div>
          <label htmlFor="playground-editor">FHIR JSON</label>
          <CodeMirror
            aria-label="FHIR JSON"
            extensions={[json()]}
            id="playground-editor"
            onChange={setText}
            value={text}
          />
          {parsed.error !== null && <p role="alert">{parsed.error}</p>}
          <button disabled={parsed.error !== null} onClick={() => void run()} type="button">
            Run
          </button>
        </div>
        <div>
          {error !== null && <ErrorCard error={error.body} />}
          {result !== null && <PlaygroundResult data={result} e2eMs={e2eMs}
            mock={health.data?.jev_client !== "live"} />}
        </div>
      </div>
    </main>
  );
}

function parseJson(text: string): { value: unknown; error: string | null } {
  try {
    return { value: JSON.parse(text) as unknown, error: null };
  } catch (caught) {
    return { value: null, error: caught instanceof Error ? caught.message : "Invalid JSON" };
  }
}

function playgroundInput(module: DemoModule, resource: unknown): CompareRequest {
  const input: CompareRequest = { resource: resource as Record<string, unknown> };
  if (module === "quality" && resource !== null && typeof resource === "object") {
    const typedResource = resource as { resourceType?: CompareRequest["resource_type"] };
    input.resource_type = typedResource.resourceType;
  }
  return input;
}

function PlaygroundResult({ data, e2eMs, mock }: {
  data: CompareResponse; e2eMs: number | null; mock: boolean;
}) {
  const jevMs = data.jev_raw.reduce((total, call) => total + call.result.latency_ms, 0);
  return <><DecisionCard data={data} />
    <ArtifactTabs response={data} flag={flagOf(data)} auditEvent={data.audit_event} />
    <LatencyLine jevMs={jevMs} e2eMs={e2eMs} mock={mock} />
  </>;
}

function flagOf(data: { jev: unknown }): Record<string, unknown> | null {
  const candidate = (data.jev as { flag_resource?: unknown }).flag_resource;
  return candidate !== null && typeof candidate === "object"
    ? candidate as Record<string, unknown> : null;
}
