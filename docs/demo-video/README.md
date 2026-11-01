Recorded with mock Jev; Benchmarks displays the existing live report `bench_20261101T001036Z`.
Chromium-measured WebM duration: **119.48 s**; size: **11,702,313 bytes**; silent, 1920×1080.
Re-record from the repository root (server is stopped automatically):
```bash
export PATH="$HOME/.nvm/versions/node/v20.19.0/bin:$PATH"
make web-build
DEMO_ENABLED=true MOCK_JEV=true .venv/bin/python -m uvicorn jev_fhir.main:app --host 127.0.0.1 --port 18760 & demo_pid=$!
trap 'kill "$demo_pid"; wait "$demo_pid"' EXIT
(cd web && npx playwright test record.video --config video/playwright.config.ts)
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

### Narrated version

- [Narrated video](jev-fhir-demo-narrated.mp4): English AI voice-over synchronized to the 14 scenes above.
- [Narration script](jev-fhir-demo-narration.md): scene timings and spoken text.

The narrated WebM and the separate WAV and MP3 audio are kept locally and aren't in git.

Voice: Microsoft Edge `en-US-GuyNeural`; AI-generated narration. Only the approved script text was sent for synthesis.
The original silent WebM is retained. Its VP8 picture stream was copied without re-encoding; the narrated WebM adds Opus audio.

Verification: full audio/video decode passed; original and narrated video packet SHA-256 hashes match.
Measured narration loudness: −16.37 LUFS integrated, −1.49 dBTP true peak. Each voice segment fits its scene window.
The WebM container reports 119.49 seconds, including Opus timing overhead.
No application source, dependencies, endpoints, or tests were changed; application test suites and HTTP curl checks were not run for this media-only task.


### Playback compatibility

For players that do not play the WebM/Opus audio, use [the narrated MP4](jev-fhir-demo-narrated.mp4), encoded as H.264 video with a default stereo AAC audio track and fast-start metadata.
The source WebM audio was decoded and measured at −17.9 dB mean / −1.2 dB peak; it contains a non-silent signal. The cause of silence in a particular player has not been confirmed.
