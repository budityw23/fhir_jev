Re-record the demo video with the new live benchmark report. Follow AGENTS.md (standing rules). Read
`docs/demo-video/README.md`, `web/video/record.video.ts` and `.phase/video.prompt.md` first; that earlier
brief's tooling facts, honesty rules and verification still apply. Finish the whole task before you stop.

## Changes (these files only)

`web/video/record.video.ts`:

1. Line 99: select `bench_20261101T001036Z` instead of `bench_20261031T150439Z`.
2. Caption 10 becomes, verbatim:
   "The mock can't read free text, so it misses this. After a fix, the live model catches it."
3. Caption 13 becomes, verbatim:
   "Live latency misses the target: about 235–470 ms at p50 against a 30 ms goal. Labels are still provisional."
4. All other captions stay exactly as they are.

`docs/demo-video/jev-fhir-demo.webm`: replace with the new recording.

`docs/demo-video/README.md`: update the report name, measured length, size and timing table.

## Must not change

Everything else, especially `web/src/`, `web/e2e/`, `src/`, `tests/`, every file in `benchmarks/results/`
and the other files in `docs/`. Don't use `git checkout`, `git restore`, `git stash`, `git reset` or
`git clean`. Don't commit.

**Mock Jev only**, `MOCK_JEV=true` explicitly. Never run `make bench-live*` or `make smoke-live`, and never
read `.env`. Displaying the existing report from disk makes no Jev call.

## Verify (real output)

1. Measure length in Chromium as the earlier brief describes. Must be ≤ 120.0 s, and the file must be one
   continuous take at 1920×1080.
2. Extract one frame per storyboard row to `web/test-results/video-frames/` and **view them**:
   - Row 10 shows `code_text` with the dengue text in the state panel, the mock's not-notifiable result,
     and the new caption, complete.
   - Rows 12 and 13 show report `bench_20261101T001036Z`, marked LIVE. Report the exact percentages on
     screen for Quality, Router and Notifiable (the report's values are 0.648, 0.814 and 0.935) and the
     p50 values (470.4, 236.3 and 235.3 ms).
   - Every UI frame shows the MOCK badge, with no blank or loading state.
3. `npm run lint`, `npm run typecheck` and `npm run test` in `web/`, with
   `export PATH="$HOME/.nvm/versions/node/v20.19.0/bin:$PATH"`. Run `npm run e2e` too: 29 passed.
4. `git status --porcelain`, and confirm no server is left running.

## Report back

Measured length, file size, the timing table, frame findings with the exact on-screen numbers, and anything
you couldn't do.
