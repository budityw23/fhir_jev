import type { Thresholds } from "./api/types";

/** A presenter preset and its ordered, keyboard-reachable sub-steps. */
export interface Scene {
  id: 0 | 1 | 2 | 3 | 4 | 5 | 6;
  title: string;
  route: string;
  fixtureId?: string;
  thresholds?: Partial<Thresholds>;
  autoAction?: "startPipeline";
  pipeline?: { source: string; ratePerS: number | null };
  note: string;
  steps?: Array<{
    fixtureId?: string;
    thresholds?: Partial<Thresholds>;
    note: string;
  }>;
}

// Fixture choices are provisional evidence from mock full report bench_20260927T120759Z:
// mixed_bundle is wrong for both Jev and rules; dbd_text_only is missed by both. The quality
// cases respectively show acceptance, NIK gating, formatting disagreement, and completeness.
export const SCENES: Scene[] = [
  {
    id: 0,
    title: "Overview",
    route: "/",
    note: "Jev makes typed, probabilistic decisions without text generation.",
  },
  {
    id: 1,
    title: "Quality",
    route: "/studio/quality",
    fixtureId: "tests/fixtures/patients/complete_patient.json",
    note: "Complete FHIR is auto-accepted; the flat state shows exactly what Jev sees.",
    steps: [
      {
        fixtureId: "tests/fixtures/patients/invalid_nik.json",
        note: "The NIK gate sends an otherwise complete record to review.",
      },
      {
        fixtureId: "benchmarks/dataset/hard/patients/nik_dotted.json",
        note: "A dotted real ID exposes the length-rule limitation.",
      },
      {
        fixtureId: "tests/fixtures/patients/minimal_patient.json",
        note: "Missing fields make this record review-needed.",
      },
      {
        fixtureId: "tests/fixtures/patients/complete_patient.json",
        thresholds: { quality_threshold: 85 },
        note: "The threshold is the product control: higher means more human review.",
      },
    ],
  },
  {
    id: 2,
    title: "Router",
    route: "/studio/router",
    fixtureId: "tests/fixtures/bundles/lab_bundle.json",
    note: "Routing exposes probabilities, not only a category.",
    steps: [
      {
        fixtureId: "tests/fixtures/bundles/immunization_bundle.json",
        note: "A focused bundle routes to immunization reporting.",
      },
      {
        fixtureId: "tests/fixtures/bundles/mixed_bundle.json",
        note: "Mixed input is wrong for both Jev and rules in the mock report.",
      },
      {
        fixtureId: "tests/fixtures/bundles/mixed_bundle.json",
        thresholds: { route_confidence_minimum: 0.99 },
        note: "The confidence floor makes ambiguity explicit: unknown goes to a human.",
      },
    ],
  },
  {
    id: 3,
    title: "Notifiable",
    route: "/studio/notifiable",
    fixtureId: "tests/fixtures/conditions/japanese_encephalitis_a83.json",
    note: "A confirmed condition produces both a Dinkes Flag and an AuditEvent.",
    steps: [
      {
        fixtureId: "tests/fixtures/conditions/common_cold_j06.json",
        note: "Common cold is not notifiable and produces no Flag.",
      },
      {
        fixtureId: "benchmarks/dataset/hard/conditions/dbd_text_only.json",
        note: "Text-only DBD is missed by both in the mock report; show that honestly.",
      },
    ],
  },
  {
    id: 4,
    title: "Pipeline",
    route: "/pipeline",
    autoAction: "startPipeline",
    pipeline: { source: "unit", ratePerS: 4 },
    note: "The unit source is 60 resources, not the original plan's 50; lanes show human work.",
  },
  {
    id: 5,
    title: "Benchmarks",
    route: "/benchmarks",
    note: "Rules win on routing today; the evidence makes that visible.",
  },
  {
    id: 6,
    title: "What's next",
    route: "/",
    note: "Low-confidence cases can move to an LLM reasoning layer and then a human.",
  },
];
