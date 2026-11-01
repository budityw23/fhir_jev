Created [jev-fhir-demo.webm](docs/demo-video/jev-fhir-demo.webm): **118.64 seconds**, **11,856,097 bytes**, silent, captioned, 1920×1080.

I extracted and viewed all 14 [review frames](web/test-results/video-frames/). Every caption is complete and legible; all UI frames retain the MOCK badge, with no blank/loading state or covered main result.

| Row | Caption timing | Frame check |
|---|---|---|
| 1 | 0.2–7.2 s | Title clear |
| 2 | 7.2–13.2 s | Conformance distinction clear |
| 3 | 13.2–22.9 s | Overview path visible |
| 4 | 23.4–30.4 s | Patient accepted; typed state visible |
| 5 | 30.7–38.7 s | NIK length 15; review result visible |
| 6 | 41.2–45.2 s | Threshold 85 sends score 80 to review |
| 7 | 45.5–52.6 s | Lab routing probabilities visible |
| 8 | 53.6–60.6 s | Floor 0.99; unknown/review visible |
| 9 | 61.0–69.0 s | Reporting card, Flag and AuditEvent tab visible |
| 10 | 69.7–76.7 s | Text-only dengue miss visible |
| 11 | 76.9–87.6 s | Pipeline visibly populated |
| 12 | 87.7–98.7 s | LIVE report, accuracy and FAIL chips visible |
| 13 | 98.7–105.8 s | LIVE latency and provisional-label warning visible |
| 14 | 105.8–118.64 s | Closing card, including recorder tail |

Only caption 11 changed: lane names now read **“auto_accepted, routed, flagged, or review.”** No captions were dropped.

One verification limitation: the unchanged UI rounds live accuracies **0.676 / 0.814 / 0.839** to **68% / 81% / 84%**. Both benchmark frames show those percentages. Data and display were preserved.

Added only the four authorized files: the video, [README](docs/demo-video/README.md), [recorder config](web/video/playwright.config.ts), and [recording spec](web/video/record.spec.ts). README contains re-record commands.

Verification passed: lint, typecheck, and the recording test (**0 → 1**, about **1.9 minutes**). Application coverage was not rerun; application source was unchanged, and the starting `web/src` diff hash still matches exactly.

Actual server health output:
```json
{"status":"ok","jev_client":"mock","jev_model":null,"version":"0.1.0"}
```

Server and verification browser stopped; ports **18760** and **18761** confirmed closed. Existing files, the live report, and an unrelated article draft were left untouched.

Open evaluator questions: none.