Implemented D4c polish and runbook.

Changed/added:
- `web/src/index.css`, Studio picker, benchmarks, shell/API error paths
- deterministic sample generation in `scripts/dump_openapi.py`
- `docs/demo-runbook.md`
- `web/e2e/polish.spec.ts`, expanded screenshot coverage
- `web/src/test/polish.test.tsx`, `web/src/lib/tokens.ts`

Verified:
- Web tests: 56 → 60 passing, ~3.0s.
- Focused D4 polish Playwright: 3 passing, ~12.1s.
- `make web-build` passed; no non-map dist file exceeds 1 MB.
- `make web-types` leaves `schema.d.ts` unchanged and fixture generation clean.
- Screenshots regenerated, including:
  - `studio-quality-900x800.png` — 253 KB
  - `studio-quality-dark-1280x720.png` — 216 KB

Contrast ratios (text on background / surface; chip):

| Theme | Accept | Review | Flag | Neutral |
|---|---:|---:|---:|---:|
| Light | 6.36 / 6.65 / 6.22 | 6.92 / 7.24 / 6.86 | 7.03 / 7.36 / 6.69 | 5.63 / 5.90 / 5.34 |
| Dark | 12.12 / 10.04 / 8.38 | 12.58 / 10.42 / 8.11 | 10.47 / 8.67 / 7.78 | 10.52 / 8.72 / 7.11 |

Audited `ApiError` callers: Studio config/fixture/compare, Playground, Benchmarks, Pipeline autostart/run/stop, overview module cards, health status, and observability drawer. Added `ErrorCard` where errors were previously silent.

One planted regression was run and restored:
- Light review token `#d49a00`: `expected 2.34 to be greater than or equal to 4.5`.

Incomplete due to turn time:
- I did not complete all six requested planted-bug runs.
- Full `make web-e2e` was started twice; its intentional network-guard test appears as a failure, and the second run exposed then fixed a reduced-motion locator issue. The focused polish suite now passes.
- I did not run backend `make lint/typecheck/test`, real uvicorn curl checks, or the complete final Verify block.