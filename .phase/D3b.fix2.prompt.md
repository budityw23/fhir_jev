D3b fix-up round 2 (the last allowed). Same rules as before. No backend changes, no new dependencies. Don't add the
kill/restart spec: the evaluator runs that check as a manual procedure.

The evaluator reproduced round 1: gates green (Vitest 42, Playwright 16, backend 411), toggle / merge / empty-note fixed.
The evaluator then planted 9 bugs itself: **only 3 were caught.** Two existing tests are vacuous, and the drawer layout is
broken in the screenshot.

## 1. Make these planted bugs fail a Vitest test (❌)
Each mutation below left all 42 tests green. Add or fix tests so that each fails, run the mutation yourself, confirm the
failure, and restore the file exactly. Report the failing summary line for each.

| Mutation (evaluator ran it; 42/42 still passed) | Why nothing caught it | What the test must do |
| --- | --- | --- |
| `ObservabilityDrawer.tsx`: delete `window.clearInterval(timer);` | `vi.useFakeTimers()` is called AFTER the drawer mounted, so the interval was created with real timers and advancing fake time never fires it | enable fake timers BEFORE rendering (use `shouldAdvanceTime` or flush promises with `advanceTimersByTimeAsync`), assert a 2nd metrics fetch after 5 s while open, then close and assert no more metrics fetches after another 10 s |
| delete `useEffect(() => subscribeLastRequest(setLastRequest), [])` | every mocked response carries the same `before-id` header | give each response a DIFFERENT `X-Request-Id`; after opening, trigger a later `api()` call (outside the drawer) with id `later-id` and assert the drawer shows `later-id` |
| `useState(getLastRequest())` → `useState(null)` | same reason (the drawer's own fetch later sets `before-id` too) | make the pre-open request's id unique (`before-id`) and the drawer's own responses carry no id / different ids; assert `before-id` is shown immediately on open (before the drawer's own fetches resolve) |
| delete the `Escape` handler | no test presses Escape | press Escape → `onClose` is called |
| `src/pages/Pipeline.tsx`: `"disconnected"` → `"connecting"` | no Pipeline indicator test | render `Pipeline` with a mocked `EventSource`; fire `onopen` → "connected"; fire `onerror` → "disconnected" |
| `src/App.tsx`: `setDrawerOpen((open) => !open)` → `setDrawerOpen(true)` | no TopBar/App toggle test | render `App` (MemoryRouter + QueryClient, mocked fetch/EventSource); click "Observability" → drawer shown, `aria-expanded="true"`; click again → drawer gone, `aria-expanded="false"` |

## 2. Playwright fixes (❌)
- Spec 5 is vacuous when the header is missing: `toContain(last?.headers()["x-request-id"] ?? "")` passes against `""`.
  Assert the last `/api/` response exists and its `x-request-id` header matches a UUID pattern, THEN assert the drawer's
  request id equals it. Avoid the race with the drawer's own polling: e.g. wait for the drawer's first metrics response,
  then read the text and compare it with the header of the most recent `/api/` response at that moment (or use
  `expect.poll`).
- The two-tab test opens `browser.newContext()`, which bypasses the auto network guard (it routes only the fixture
  page's context). Use the fixture `page` plus `page.context().newPage()` for the second tab so the guard covers both.

## 3. Drawer layout (❌, from the evaluator viewing `drawer-1280x720.png`)
- It renders as a short box pinned top-right: the JSON lines are clipped at the right edge, the decision log is a tiny
  box, and the metrics table spills out below the drawer over the page.
- Make it a real slide-over: `position: fixed`, full viewport height, right-aligned, width about `min(36rem, 100vw)`,
  its own `overflow-y: auto`, a visible border/shadow, above the page (`z-index`), and page content stays usable.
- Decision JSON lines: wrap long lines (`white-space: pre-wrap; overflow-wrap: anywhere`) or a bounded box with its own
  scroll, so nothing is clipped. The metrics tables fit within the drawer width.
- Show the duration with its unit (e.g. "4.5 ms" via the existing `milliseconds` formatter).
- The "Observability" TopBar button must stay visible and clickable while the drawer is open (so it can toggle it
  closed); don't cover it.
The evaluator will view the regenerated `drawer-*.png`.

## Verify
```bash
export PATH="$HOME/.nvm/versions/node/v20.19.0/bin:$PATH"
make web-test && make web-build && make web-e2e      # run make web-e2e twice
awk 'length > 100' $(git ls-files -o -m --exclude-standard web | grep -E '\.(ts|tsx|js|css)$' | grep -v schema.d.ts) \
  $(git ls-files web | grep -E '\.(ts|tsx|js)$' | grep -v schema.d.ts)                        # nothing
make lint && make typecheck && make test                                                       # backend 411
```

## Report back with
Changed files; Vitest 42 → after; both `make web-e2e` summaries; for each of the 6 mutations in item 1, the Vitest summary
line showing the failure; a short description of the regenerated drawer screenshot; anything you couldn't do, stated
plainly at the end.
