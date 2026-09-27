import { useEffect, useMemo, useState } from "react";
import {
  Navigate,
  useLocation,
  useNavigate,
  useParams,
  useSearchParams,
} from "react-router-dom";
import { ApiError, subscribeLastRequest } from "../api/client";
import {
  useCompare,
  useDemoConfig,
  useFixture,
  useHealth,
} from "../api/queries";
import type { DemoModule, ThresholdOverrides, Thresholds } from "../api/types";
import { ErrorCard } from "../components/shell/ErrorCard";
import { ArtifactTabs } from "../components/studio/ArtifactTabs";
import { DecisionCard } from "../components/studio/DecisionCard";
import { FixturePicker } from "../components/studio/FixturePicker";
import { FlatStateTable } from "../components/studio/FlatStateTable";
import { JsonView } from "../components/studio/JsonView";
import { LatencyLine } from "../components/studio/LatencyLine";
import { QuestionBox } from "../components/studio/QuestionBox";
import { ThresholdSliders } from "../components/studio/ThresholdSliders";
import { VerdictStrip } from "../components/studio/VerdictStrip";
import { debounce } from "../lib/debounce";

const modules: DemoModule[] = ["quality", "router", "notifiable"];

/** Run a selected fixture through one Jev decision module. */
export function Studio() {
  const { module: param } = useParams();
  const location = useLocation();
  if (!modules.includes(param as DemoModule))
    return <Navigate to="/studio/quality" replace />;
  return <StudioPage key={location.key} module={param as DemoModule} />;
}

function StudioPage({ module }: { module: DemoModule }) {
  const [params] = useSearchParams();
  const navigate = useNavigate();
  const config = useDemoConfig();
  const health = useHealth();
  const fixtureId = params.get("fixture");
  const fixture = useFixture(fixtureId);
  const urlKey = params.toString();
  const urlOverrides = readThresholdOverrides(params);
  const [overrideState, setOverrideState] = useState({
    urlKey,
    overrides: urlOverrides,
  });
  if (overrideState.urlKey !== urlKey)
    setOverrideState({ urlKey, overrides: urlOverrides });
  const [sentThresholds, setSentThresholds] = useState<Thresholds | null>(null);
  const [e2eMs, setE2eMs] = useState<number | null>(null);
  const thresholds = useMemo(
    () =>
      config.data
        ? ({
            ...config.data.thresholds,
            ...overrideState.overrides,
          } as Thresholds)
        : null,
    [config.data, overrideState.overrides],
  );
  const delayedCompare = useMemo(
    () => debounce((next: Thresholds) => setSentThresholds(next), 250),
    [],
  );
  useEffect(() => {
    if (thresholds !== null) delayedCompare(thresholds);
  }, [delayedCompare, thresholds]);
  useEffect(
    () =>
      subscribeLastRequest((request) => {
        if (request.path.startsWith(`/api/v1/demo/compare/${module}`)) {
          setE2eMs(request.durationMs);
        }
      }),
    [module],
  );
  const overrides = useMemo(
    () => changedThresholds(sentThresholds, config.data?.thresholds ?? null),
    [sentThresholds, config.data],
  );
  const input =
    fixture.data && fixtureId && sentThresholds
      ? { resource: fixture.data, fixture_id: fixtureId, thresholds: overrides }
      : null;
  const compare = useCompare(module, input);
  const selectFixture = (id: string) => {
    navigate(`/studio/${module}?fixture=${encodeURIComponent(id)}`);
  };
  if (config.error instanceof ApiError) {
    return (
      <main>
        <ErrorCard error={config.error.body} />
      </main>
    );
  }
  return (
    <main>
      <h2>Studio</h2>
      <div className="studio-tabs">
        {modules.map((item) => (
          <button
            aria-pressed={module === item}
            key={item}
            onClick={() => navigate(`/studio/${item}`)}
          >
            {item}
          </button>
        ))}
      </div>
      <div className="studio-grid">
        <div>
          <FixturePicker
            module={module}
            value={fixtureId}
            onChange={selectFixture}
          />
          {fixture.error instanceof ApiError && <ErrorCard error={fixture.error.body} />}
          {fixture.data && (
            <>
              <h3>Raw FHIR</h3>
              <JsonView value={fixture.data} />
            </>
          )}
        </div>
        <div>
          {compare.data && (
            <>
              <FlatStateTable state={compare.data.serialized_state} />
              <QuestionBox
                questions={questionsFor(module, config.data?.questions ?? {})}
              />
            </>
          )}
        </div>
        <div>
          {compare.error instanceof ApiError && (
            <ErrorCard error={compare.error.body} />
          )}
          {compare.data && thresholds && (
            <DecisionContents
              data={compare.data}
              module={module}
              thresholds={thresholds}
              onChange={(next) =>
                setOverrideState({
                  urlKey,
                  overrides:
                    changedThresholds(next, config.data?.thresholds ?? null) ??
                    {},
                })
              }
              onReset={() => setOverrideState({ urlKey, overrides: {} })}
              e2eMs={e2eMs}
              mock={health.data?.jev_client !== "live"}
            />
          )}
        </div>
      </div>
    </main>
  );
}

type DecisionContentsProps = {
  data: import("../api/types").CompareResponse;
  module: DemoModule;
  thresholds: Thresholds;
  onChange: (value: Thresholds) => void;
  onReset: () => void;
  e2eMs: number | null;
  mock: boolean;
};

function DecisionContents(props: DecisionContentsProps) {
  const { data, module, thresholds, onChange, onReset, e2eMs, mock } = props;
  const jevMs = data.jev_raw.reduce(
    (total, call) => total + call.result.latency_ms,
    0,
  );
  return (
    <>
      <DecisionCard data={data} />
      <ThresholdSliders
        module={module}
        value={thresholds}
        onChange={onChange}
      />
      <button onClick={onReset}>Reset</button>
      <VerdictStrip
        verdict={data.verdict}
        jevDecision={data.jev_decision}
        ruleDecision={data.rule.decision}
        groundTruth={data.ground_truth}
      />
      <ArtifactTabs
        response={data}
        flag={flagOf(data)}
        auditEvent={data.audit_event}
      />
      <LatencyLine jevMs={jevMs} e2eMs={e2eMs} mock={mock} />
    </>
  );
}

function changedThresholds(
  value: Thresholds | null,
  defaults: Thresholds | null,
): ThresholdOverrides | null {
  if (value === null || defaults === null) return null;
  const entries = Object.entries(value).filter(([key, current]) => {
    return current !== defaults[key as keyof Thresholds];
  });
  return entries.length === 0
    ? null
    : (Object.fromEntries(entries) as ThresholdOverrides);
}

function readThresholdOverrides(params: URLSearchParams): ThresholdOverrides {
  const values: ThresholdOverrides = {};
  for (const key of [
    "quality_threshold",
    "route_confidence_minimum",
    "notifiable_confirmed",
    "notifiable_review",
  ] as const) {
    const value = params.get(key);
    if (value !== null && Number.isFinite(Number(value)))
      values[key] = Number(value) as never;
  }
  return values;
}

/** Select the exact configured Jev questions for one Studio module. */
export function questionsFor(
  module: DemoModule,
  questions: Record<string, string>,
): string[] {
  const values = Object.entries(questions);
  if (module === "quality") {
    return values
      .filter((item) => {
        return (
          item[0] === "QUALITY_SCORE_QUESTION" ||
          item[0] === "NIK_VALIDATION_STATEMENT"
        );
      })
      .map(([, value]) => value);
  }
  if (module === "router") {
    return values
      .filter(([key]) => key === "ROUTE_QUESTION")
      .map(([, value]) => value);
  }
  return values
    .filter(([key]) => key === "NOTIFIABLE_STATEMENT")
    .map(([, value]) => value);
}

function flagOf(data: { jev: unknown }): Record<string, unknown> | null {
  const candidate = (data.jev as { flag_resource?: unknown }).flag_resource;
  return candidate !== null && typeof candidate === "object"
    ? (candidate as Record<string, unknown>)
    : null;
}
