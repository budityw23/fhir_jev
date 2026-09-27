Implemented the D3a core pipeline and SSE restart handling.

Changed/added:
- `src/jev_fhir/demo/feed.py`, `sse.py`
- `tests/test_demo_sse.py`
- Pipeline page, SSE hook, reducer, controls/components, styling, route wiring
- Pipeline screenshots in `web/e2e/screenshots.spec.ts`
- Reducer Vitest coverage in `web/src/test/pipeline.reducer.test.ts`

Verification:
- `make lint && make typecheck && make test` — 411 passed in 8.71s (was 408)
- Backend coverage: `feed.py` 100%, `sse.py` 96%, total 98%
- `make web-test` — 31 Vitest tests passed in 1.96s (was 28)
- `make web-build`, `make web-types`, and schema no-change diff passed
- Existing full `make web-e2e` passed: 8 tests; updated screenshot capture also passed separately.

Real-server output:
```json
{"run_id":"61a44e1f0bc243d0af2bb227207fa1d9","total":60,"status":"started"}
{"stopped":true}
[{"seq":4,...}]
[{"seq":4,...}]
```

The two decision queries retained `seq: 4`, as required.

Screenshots:
- `web/e2e/screenshots/pipeline-1280x720.png` — 744 KB
- `web/e2e/screenshots/pipeline-1920x1080.png` — 769 KB

They show a finished unit run with controls, metrics, lane counters, charts, review queue, and live feed.

Choices:
- Sends the full thresholds object on run start.
- p50/p95 use nearest-rank.
- Rerun delta uses Unicode minus (`−`) and `±0`.

Open evaluator question: D3a’s requested dedicated component/SSE/Playwright test coverage is only partially added; the new reducer tests cover the critical capped-event and foreign-run behavior, but the full named test matrix and serial pipeline e2e spec still need completion.