# Jev × FHIR demo runbook

## Start and safety

1. From a cold checkout, run `make demo`, then open `http://127.0.0.1:8000/demo`.
2. Confirm the health dot is healthy and the mode badge matches the intended mode. The `.env` value
   is the default when no override is given. For live mode, keep the key only in `.env`, run
   `make smoke-live`, then run `MOCK_JEV=false make demo`; verify `/health` reports `jev_client`
   `live` and the badge says LIVE. `MOCK_JEV=true make demo` is the offline fallback; verify
   `/health` reports `jev_client` `mock` and the badge says MOCK.
3. The browser stays on localhost; never type a resource during the main flow. Use Playground only
   for Q&A. Set browser zoom to 125%, turn notifications off, and put presenter notes on the second
   screen.

## Live fallback drill (under 30 seconds)

If live Jev is slow, rate-limited, or unavailable: stop the live server with `Ctrl-C`, then run
`MOCK_JEV=true make demo`. Reopen `http://127.0.0.1:8000/demo`, verify `/health` reports `mock`, use `1`–`6` to return to the
current scene, and point out the persistent MOCK badge and the mock disclaimer. Do not claim mock
accuracy is live-model evidence.

## Scene flow

`→` advances a sub-step before the next scene; `←` goes back. `1`–`6` jump to scenes 1–6, `R`
resets the current scene, `F` toggles 100%/125% type, `O` opens observability, and `N` shows notes.

| Scene | Keys / fixture | Point at |
| --- | --- | --- |
| 0 Overview | Start at Overview; `→` | Animated FHIR → serializer → Jev → action path; mode badge and health dot. |
| 1 Quality | `→`: `complete_patient` → `invalid_nik` → `nik_dotted` → `minimal_patient` → complete at threshold 85 | Flat state, NIK gate, then how the threshold changes automation. |
| 2 Router | `→`: `lab_bundle` → `immunization_bundle` → `mixed_bundle` → mixed at 0.99 | Probability bars, both-wrong mock result, then `unknown` as human review. |
| 3 Notifiable | `→`: `japanese_encephalitis_a83` → `common_cold_j06` → `dbd_text_only` | Confirmed report card, generated FHIR Flag, and AuditEvent. State honestly when mock misses DBD. |
| 4 Pipeline | `→` starts unit ingestion at 4/s | Lanes, review queue, counters, latency and confidence charts. |
| 5 Benchmarks | `→` | PRD chips, latency, calibration, disagreement links, and mock disclaimer. |
| 6 What's next | `→` | Dimmed low-confidence → LLM reasoning layer → human branch. |

The scene fixtures are provisional mock-full-report choices. Re-run and re-check them after
`make bench-live-full`; live outputs, not mock values, determine the final demo talk track.

## Demo Day checklist

- [ ] `make lint typecheck test bench` is green on the demo machine.
- [ ] `make demo` started cold; `/demo` and the mode badge are correct.
- [ ] `make smoke-live` passed on the venue network before a live presentation.
- [ ] The latest benchmark report is for the mode being presented.
- [ ] The fallback drill above returned to the scene in under 30 seconds.

## Short Q&A

**Why not just rules?** Rules stay as a visible baseline, but brittle edge cases and uncertainty
need a probabilistic decision layer and a human-review lane.

**How is confidence calibrated?** The benchmark page compares confidence buckets with observed
accuracy against the y=x reference; thresholds turn that evidence into an automation policy.

**What data does Jev see?** Flattened, typed FHIR R4 state and fixed decision questions, shown in
the Studio “What Jev sees” panel; it is not free-form prompt generation.

**PHI?** This demo uses synthetic fixtures. The demo displays only the flattened decision state;
production data handling requires the relevant privacy controls and agreements.
