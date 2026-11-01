Recorded with mock Jev; Benchmarks displays the existing live report `bench_20261101T054220Z`.
Chromium-measured WebM duration: **115.60 s**; size: **11,450,763 bytes**; silent, 1920×1080.
Re-record from the repository root (server is stopped automatically):
```bash
export PATH="$HOME/.nvm/versions/node/v20.19.0/bin:$PATH"
make web-build
DEMO_ENABLED=true MOCK_JEV=true .venv/bin/python -m uvicorn jev_fhir.main:app --host 127.0.0.1 --port 18760 & demo_pid=$!
trap 'kill "$demo_pid"; wait "$demo_pid"' EXIT
(cd web && npx playwright test record.video --config video/playwright.config.ts)
```
| Row | Seconds (caption visible) | Scene |
| --- | --- | --- |
| 1 | 0.16–7.35 | Jev × FHIR title |
| 2 | 7.35–13.35 | Conformance versus decisions |
| 3 | 13.36–21.36 | Overview animated path |
| 4 | 21.77–28.78 | Complete Patient |
| 5 | 29.13–37.14 | Invalid NIK |
| 6 | 40.75–44.75 | Threshold 85; dotted/minimal previews between rows 5 and 6 |
| 7 | 45.09–51.09 | Lab Bundle routing |
| 8 | 52.11–59.12 | Mixed Bundle, floor 0.99 |
| 9 | 59.48–67.49 | Japanese encephalitis, Flag |
| 10 | 68.16–76.37 | Text-only dengue missed by mock; live catches it after fix |
| 11 | 76.52–85.52 | Pipeline lanes; actual lane names in caption |
| 12 | 85.64–96.64 | Latest LIVE accuracy: quality 66%, router 95%, notifiable 94% |
| 13 | 96.64–103.64 | Latest LIVE latency: p50 458.0 / 232.8 / 236.4 ms |
| 14 | 103.65–109.85 | Closing card |
| Tail | 109.85–115.60 | Closing card remains through recorder tail |

### Narrated version

The narrated MP4 and its script predate these results and still say rules win routing.

- [Narrated video](jev-fhir-demo-narrated.mp4): English AI voice-over synchronized to the earlier 14-scene take.
- [Narration script](jev-fhir-demo-narration.md): scene timings and spoken text.

The narrated WebM and the separate WAV and MP3 audio are kept locally and aren't in git.

Voice: Microsoft Edge `en-US-GuyNeural`; AI-generated narration. Only the approved script text was sent for synthesis.
The narrated version used the earlier silent WebM: its VP8 picture stream was copied without re-encoding, and the narrated WebM adds Opus audio.

Verification: full audio/video decode passed; original and narrated video packet SHA-256 hashes match.
Measured narration loudness: −16.37 LUFS integrated, −1.49 dBTP true peak. Each voice segment fits its scene window.
The WebM container reports 119.49 seconds, including Opus timing overhead.
For that narration-only conversion, no application source, dependencies, endpoints, or tests were changed; application test suites and HTTP curl checks were not run.


### Playback compatibility

For players that do not play the WebM/Opus audio, use [the narrated MP4](jev-fhir-demo-narrated.mp4), encoded as H.264 video with a default stereo AAC audio track and fast-start metadata.
The source WebM audio was decoded and measured at −17.9 dB mean / −1.2 dB peak; it contains a non-silent signal. The cause of silence in a particular player has not been confirmed.
