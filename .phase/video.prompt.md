Record a demo video of the Jev × FHIR web UI: at most 120 seconds, silent, captioned. This is not a
plan phase, but AGENTS.md's standing rules apply. Read `docs/demo-runbook.md`, `web/src/scenes.ts`
and `web/e2e/presenter.spec.ts` first.

**Finish the whole task before you stop.** Earlier sessions stopped early. Don't end your turn
until the video exists, its length is measured, and you have looked at the frames.

## Who it's for

Health-IT and FHIR engineers who have never seen this project. In two minutes they should learn what
it is, see the real UI, and understand how it differs from FHIR conformance validation.

## Environment and tooling facts (checked, don't re-derive)

- Node for `web/`: `export PATH="$HOME/.nvm/versions/node/v20.19.0/bin:$PATH"`.
- Playwright's `recordVideo` / `video` option is the recorder. Its bundled ffmpeg
  (`~/.cache/ms-playwright/ffmpeg-1013/ffmpeg-linux`) writes WebM only and has no decoders, so MP4,
  concatenation, re-encoding and burned-in text are impossible. There is no system ffmpeg, no audio
  and no text-to-speech. Don't install anything. The result is **one continuous take in one page**,
  and all captions and title cards are HTML drawn in the browser.
- `make web-build` builds `web/dist` from the current working tree. The uncommitted changes in
  `web/src` are the owner's latest polish and **must** appear in the video.
- Server (run it yourself on a free port, then stop it):
  `DEMO_ENABLED=true MOCK_JEV=true .venv/bin/python -m uvicorn jev_fhir.main:app --host 127.0.0.1 --port 18760`

## Hard rules

- **Mock Jev only.** `MOCK_JEV=true` explicitly, whatever `.env` says. Never run `make bench-live*`,
  `make smoke-live` or anything else that calls the live API. Don't read or print `.env`.
- The Benchmarks scene displays the existing **live** report `bench_20261031T150439Z` from disk. That
  makes no Jev call. **Never delete or modify `benchmarks/results/bench_20261031T150439Z.*`**; the
  owner keeps them, despite the general hygiene rule.
- **Don't modify** `src/`, `web/src/`, `web/e2e/`, `web/package.json`, `web/package-lock.json`,
  `web/playwright.config.ts`, `web/tsconfig*.json`, the Makefile, fixtures, labels or `pyproject.toml`.
- Don't commit. No new dependencies.
- **Honesty:** the persistent MOCK badge must stay visible on every UI scene, never hidden or covered.
  Don't alter displayed data, hide failing chips, or stub API responses. If a caption below turns out
  to be false for what the screen really shows, don't bend the screen: change nothing, keep the
  caption out, and report it at the end.

## What to add (these paths only)

- `web/video/playwright.config.ts`: own config with `testDir` here, chromium, 1920×1080 viewport and
  `video: { mode: "on", size: { width: 1920, height: 1080 } }`, generous test timeout, `outputDir`
  under `web/test-results/`, `reuseExistingServer: true` pointing at port 18760.
- `web/video/record.spec.ts`: drives the UI and draws the captions.
- `docs/demo-video/jev-fhir-demo.webm`: the final video.
- `docs/demo-video/README.md`: under 25 lines. The exact commands to re-record, the measured length,
  and the scene timing table. State that it was recorded with mock Jev, and that the Benchmarks scene
  shows the live report.

Throwaway frames go under `web/test-results/video-frames/` (git-ignored). Leave them there, the
evaluator views them.

## Captions

Inject one overlay element from the spec with `page.evaluate` / `addInitScript`, with
`pointer-events: none`. It's a lower-third bar: dark translucent background, white text, at least 30px
at 1920×1080, at most two lines, placed where it doesn't cover the mock badge or the main result. Title
cards are a full-page overlay in the same way. Re-inject after any full navigation. Nothing here goes
into the app bundle. Drive the app the way a presenter would: the real keys (`→`, `1`–`6`), clicking
the real controls. Wait for the app to show the result before starting a caption's hold time; never
press keys right after `goto`. Don't turn on the presenter notes strip.

## Storyboard (fixed; target 110 s, hard maximum 120 s)

Use these captions verbatim. Each stays up at least 3.5 s. Times are targets; you may rebalance them,
but keep the order and stay under the maximum.

| # | Target | Screen | Caption |
| --- | --- | --- | --- |
| 1 | 0–8 s | Title card | **Jev × FHIR** / "A decision layer for FHIR data" |
| 2 | 8–14 s | Title card | "FHIR conformance asks: is this resource valid?" / "This project asks: what should we do with it?" |
| 3 | 14–24 s | Overview, let the animated path run | "FHIR is flattened into typed state. Jev returns a decision and a confidence, not generated text." |
| 4 | 24–32 s | Studio Quality, `complete_patient` | "A complete Patient is scored and auto-accepted. This panel shows exactly what Jev sees." |
| 5 | 32–41 s | `→` `invalid_nik` | "Also valid FHIR. But the NIK has 15 digits, not 16, so it goes to human review." |
| 6 | 41–47 s | `→` through `nik_dotted` and `minimal_patient`, briefly, to the threshold-85 step | "The threshold is the control: raise it, and more records go to a person." |
| 7 | 47–54 s | `2` Router, `lab_bundle` | "Which pipeline should get this Bundle? Routing shows probabilities, not only a category." |
| 8 | 54–62 s | `→` to `mixed_bundle` at floor 0.99 | "Below the confidence floor, the answer is unknown, and a person decides." |
| 9 | 62–71 s | `3` Notifiable, `japanese_encephalitis_a83` | "A notifiable disease produces a FHIR Flag for the health office and an AuditEvent." |
| 10 | 71–79 s | `→` `→` to `dbd_text_only` | "Dengue written only as free text is missed. The live model misses this one too." |
| 11 | 79–91 s | `4` Pipeline at 4/s, lanes filling | "In a stream, each resource lands in a lane: accepted, routed, flagged, or sent to review." |
| 12 | 91–104 s | `5` Benchmarks, **select the live report `bench_20261031T150439Z`**, scroll to the accuracy and latency evidence | "Live results on 204 synthetic fixtures. Jev beats rules on quality and notifiable disease. Rules win routing." |
| 13 | 104–112 s | Same page | "Live latency misses the target: about 260–490 ms at p50 against a 30 ms goal. Labels are still provisional." |
| 14 | 112–118 s | Title card | "A proof of concept on synthetic data. Conformance first, decisions on top." |

Scene 11: check the lane names on the real screen and match the caption to them (this is the only
caption you may reword, for lane names only). Let the run reach a visibly populated state; a video
that stops mid-run is fine.

## Verify (all of it, real output)

1. **Length:** load the WebM in Chromium with Playwright in a `<video>` element and read
   `duration`. WebM from Playwright can report `Infinity`; if so, seek to a very large time and read
   `duration` again. Report the measured number. Must be ≤ 120.0 s. If it's over, shorten holds and
   re-record.
2. **Frames:** from that same `<video>`, seek and screenshot one frame per storyboard row into
   `web/test-results/video-frames/`, then **view them**. For each, confirm: caption legible and
   complete, MOCK badge visible on UI scenes, no blank or loading state, nothing important covered.
   Row 12 and 13 frames must show the LIVE report's numbers (0.676, 0.814, 0.839 for Jev).
3. `npm run lint` and `npm run typecheck` in `web/` still pass, and `git status` shows only the paths
   above as new. The `web/src` diff must be byte-identical to what you started with.
4. The server is stopped, and no stray processes are left.

## Report back

Measured length, file size, the scene timing table, what each frame check found, every caption you
changed or dropped and why, and anything you couldn't do.
