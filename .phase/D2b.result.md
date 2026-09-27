Implemented D2b Overview and Studio.

Changed/added:
- `web/src/App.tsx`, `api/types.ts`, `index.css`
- Overview: `ArchitectureDiagram.tsx`, `ModuleCard.tsx`, `pages/Overview.tsx`
- Studio: all 14 contract components plus `pages/Studio.tsx`
- Tests: `web/src/test/studio.test.tsx`, `web/e2e/studio.spec.ts`

Studio props are exported as:
`FixturePickerProps`, `JsonViewProps`, `FlatStateTableProps`, `QuestionBoxProps`,
`DecisionCardProps`, `ScoreGaugeProps`, `LevelDistributionProps`,
`ProbabilityBarsProps`, `NoulMeterProps`, `DinkesCardProps`,
`ThresholdSlidersProps`, `VerdictStripProps`, `ArtifactTabsProps`,
`LatencyLineProps`.

Verification:
- Web Vitest: 12 → 15 tests, 6 files passed, 1.56s.
- Playwright: 2 → 6 tests, all passed, 8.6s.
- `make web-build`: passed; no non-map asset exceeds 1 MB.
- `make lint && make typecheck && make test`: passed, backend unchanged at 408 tests, 8.64s, 98% total coverage.
- No frontend coverage tool is configured in D2a, so per-file frontend coverage is unavailable.

Real-server curl output:

```text
HTTP/1.1 200 OK
content-type: text/html; charset=utf-8
x-request-id: 32082d5b-c4f2-47d4-bc99-bd678f9949ff
x-request-duration-ms: 11.667
```

```text
{'module': 'quality', 'jev_decision': 'review_needed',
 'lane': 'review', 'lane_reason': 'score 80 < threshold 85'}
```

Manual smoke via the real built demo showed the Overview shell at `/demo`; Studio quality renders fixture selection, raw FHIR, serialized state, questions, decision card, threshold controls, verdict, artifacts, and latency. Playwright additionally exercised quality threshold flipping, router override, notifiable Flag/Dinkes visibility, and deep-link restoration.

Additive internal helpers only: threshold-delta calculation, question selection, and Flag extraction; no backend changes or contract redesign.

Open question for evaluator: none.