Recorded with mock Jev; Benchmarks displays the existing live report `bench_20261101T001036Z`.
Chromium-measured WebM duration: **119.48 s**; size: **11,702,313 bytes**; silent, 1920×1080.
Re-record from the repository root (server is stopped automatically):
```bash
export PATH="$HOME/.nvm/versions/node/v20.19.0/bin:$PATH"
make web-build
DEMO_ENABLED=true MOCK_JEV=true .venv/bin/python -m uvicorn jev_fhir.main:app --host 127.0.0.1 --port 18760 & demo_pid=$!
trap 'kill "$demo_pid"; wait "$demo_pid"' EXIT
(cd web && npx playwright test --config video/playwright.config.ts)
```
| Row | Approximate seconds (caption hold; transitions between rows) | Scene |
| --- | --- | --- |
| 1 | 0.17–7.17 | Jev × FHIR title |
| 2 | 7.18–14.29 | Conformance versus decisions |
| 3 | 14.30–23.30 | Overview animated path |
| 4 | 23.73–30.74 | Complete Patient |
| 5 | 31.10–39.10 | Invalid NIK |
| 6 | 41.54–45.54 | Threshold 85; dotted/minimal previews at 39.10–41.54 |
| 7 | 45.88–53.08 | Lab Bundle routing |
| 8 | 54.13–61.14 | Mixed Bundle, floor 0.99 |
| 9 | 61.48–69.48 | Japanese encephalitis, Flag |
| 10 | 70.15–77.15 | Text-only dengue missed by mock; live catches it after fix |
| 11 | 77.31–88.46 | Pipeline at 4/s; actual lane names in caption |
| 12–14 | 88.57–99.57 / 99.57–106.58 / 106.58–119.48 | Live accuracy / latency / closing card (including recorder tail) |
