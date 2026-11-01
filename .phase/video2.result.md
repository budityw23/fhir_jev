Replaced the [video](/home/budi/code/sphere_project/FHIR_JEV/docs/demo-video/jev-fhir-demo.webm) and updated the recorder and README.

Chromium measured **119.48 s**, **1920×1080**, **11,702,313 bytes**. One continuous, silent take.

| Row | Seconds | Scene |
|---|---|---|
| 1 | 0.17–7.17 | Title |
| 2 | 7.18–14.29 | Conformance versus decisions |
| 3 | 14.30–23.30 | Overview |
| 4 | 23.73–30.74 | Complete Patient |
| 5 | 31.10–39.10 | Invalid NIK |
| 6 | 41.54–45.54 | Threshold 85 |
| 7 | 45.88–53.08 | Lab routing |
| 8 | 54.13–61.14 | Confidence floor |
| 9 | 61.48–69.48 | Notifiable Flag |
| 10 | 70.15–77.15 | Text-only dengue |
| 11 | 77.31–88.46 | Pipeline |
| 12 | 88.57–99.57 | Live accuracy |
| 13 | 99.57–106.58 | Live latency |
| 14 | 106.58–119.48 | Closing, including recorder tail |

Viewed all 14 extracted frames, retained in `web/test-results/video-frames/`. Captions are complete; every UI frame shows MOCK without blank/loading states. Row 10 shows `code_text: Demam berdarah dengue (DBD)`, `not_notifiable`, and the new caption.

Rows 12–13 show `bench_20261101T001036Z`, marked LIVE:

| Module | On-screen accuracy | p50 |
|---|---:|---:|
| Quality | 65% | 470.4 ms |
| Router | 81% | 236.3 ms |
| Notifiable | 94% | 235.3 ms |

Lint and typecheck passed; **60 unit tests passed (4.59 s)**; **29 e2e tests passed (43.5 s)**. No tests were added. The recorder’s report assertion changed from `68%` to `65%`; all other captions remain unchanged.

Actual health curl output:
```json
{"status":"ok","jev_client":"mock","jev_model":null,"version":"0.1.0"}
```

Ran `git status --porcelain` and verified protected-file hashes. Only the three authorized files were edited by this task. No servers or recorder processes remain. No live Jev calls, unresolved limitations, or evaluator questions.