# Valid FHIR Is Not the Same as a Decision

*Draft, Nov 1, 2026 · @budi · All numbers come from the live benchmark `bench_20261101T001036Z`.*

A clinic sends you a Patient resource. It parses as R4. The structure is correct, the name is there,
the birth date is there. The national ID has 15 digits instead of 16.

Another clinic sends a Condition coded as dengue. It's also well-formed. Its `verificationStatus` is
`refuted`, so the patient doesn't have dengue.

Both resources can pass FHIR validation. Neither should be handled like a normal record. The first
needs a person to check it, and the second must not trigger a dengue report to the health office.

Validation has done its job in both cases. The remaining question belongs to your pipeline: **what
should happen to this resource now?** I built a small prototype to test whether a fast decision model
can answer that question, and measured it against plain rules. It won in some places and lost in
others.

<!-- VIDEO: embed docs/demo-video/jev-fhir-demo.webm here once hosted (about 2 minutes, silent, captioned) -->

## What conformance does, and where it stops

FHIR conformance checks a resource against a specification: the base R4 spec, plus any profiles and
implementation guides you apply. It covers structure, data types, cardinality, terminology bindings
and invariants. The HL7 Validator and a server's `$validate` operation are the usual tools.

This is essential, and nothing here replaces it. Its output is about the resource's relationship to a
spec: conformant or not, with a list of issues.

Your pipeline needs different answers:

| | FHIR conformance | Decision layer |
| --- | --- | --- |
| **Question** | Does this resource meet the spec? | What should we do with it? |
| **Answer** | Pass or fail, with issues | An action, with a confidence |
| **Defined by** | A published spec or profile | Your workflow and risk tolerance |
| **Same input, same result?** | Yes | Depends on the thresholds you set |
| **When unsure** | Doesn't apply | Sends it to a person |

Profiles can cover more of this than people assume. A FHIRPath invariant could enforce a 16-digit
national ID, so the NIK example above doesn't strictly need a model. The boundary isn't "rules on one
side, AI on the other." It's between *is this correct?* and *what happens next?*

## What I built

Jev × FHIR is a FastAPI service that sits between a FHIR R4 source and downstream workflows. It makes
three decisions, each using one primitive of Typesafe AI's Jev model. Jev returns a typed judgment with
a confidence and generates no text.

| Decision | Primitive | Output |
| --- | --- | --- |
| Is this resource good enough to accept automatically? | Score, plus Noul for the NIK | A 0–100 score, then accept or review |
| Which pipeline should get this Bundle? | Choice | One category from a fixed list, or `unknown` |
| Must this Condition be reported? | Noul | Yes or no with a probability, plus a FHIR Flag and AuditEvent |

The order matters. Every serializer parses the resource with `fhir.resources` first, so a resource
that fails structural parsing raises an error before any Jev call. That parsing is lighter than full
profile and terminology validation, and it makes the design explicit: **conformance first, decisions
on top.**

After parsing, the resource is flattened into a small typed state. Jev doesn't receive the raw NIK.
It receives `identifier_value_length`, plus flags like `has_birth_date`. The Studio page in the demo
shows this exact state, so you can see what the model saw.

Thresholds turn a judgment into an action. Raise the quality threshold and more records go to people.
Set a confidence floor on routing and anything below it becomes `unknown`. Each resource ends up in one
of four lanes: auto-accepted, routed, flagged to Dinkes (the local health office), or the review queue.

The review queue is the piece conformance has no equivalent for. A decision layer can say "I'm not
sure" and hand the case to a person.

## The results

I benchmarked Jev against hand-written rules on 204 synthetic fixtures, including a deliberately hard
set.

| Decision | Fixtures | Jev | Rules | PRD target |
| --- | ---: | ---: | ---: | --- |
| Quality scoring (accuracy) | 71 | **0.648** | 0.549 | ≥ 0.85, missed |
| Bundle routing (accuracy) | 102 | 0.814 | **0.922** | ≥ 0.90, missed |
| Notifiable disease (accuracy) | 31 | **0.935** | 0.677 | no target |
| Notifiable disease (recall) | 31 | **0.895** | 0.579 | ≥ 0.95, missed |
| Notifiable disease (precision) | 31 | **1.000** | 0.846 | ≥ 0.80, met |

So Jev beat the rules on two decisions, lost on one, and missed most of the targets I set in advance.
The details are more useful than the scoreboard.

**The biggest gain came from fixing my own bug.** My first live run scored 0.839 on notifiable disease.
Reading the misses, I found that the serializer dropped `code.text`, so a disease written only as
"Demam berdarah dengue" or "TB paru" reached the model as blank. I added that one field and re-ran.
Exactly three disease fixtures flipped, all of them the text-only cases, and accuracy rose to 0.935. Before
blaming a model, check what you actually sent it.

**Where Jev earned its place: context.** On the 14 hard Condition fixtures, Jev scored 0.929 and the
rules 0.357. The rules reported a refuted dengue case and a cholera record marked `entered-in-error` as
real. Jev confirmed neither and sent both to human review. It also caught dengue and tuberculosis coded
only in SNOMED, which an ICD-10 lookup can't see.

To be fair to the rules, the baseline is an exact ICD-10 match, and some of its losses are cheap to
fix. Prefix matching would handle subcodes like `A15.0`. Checking `verificationStatus` would handle the
refuted case. A sensible team would write those rules, and the gap would shrink.

**Where rules won: routing.** But the raw score hides how the errors differ. Twelve of Jev's 19 errors
were encounter Bundles that came back as `unknown`, at 0.39–0.62 confidence. That's a person doing
extra work, and it's the failure mode you'd choose. The other seven are worse: Bundles that should
have been `unknown` were sent to a pipeline at 0.81–1.00 confidence. The rules made eight mistakes of
that same kind.

**On disease reports, the review lane did its job.** Of the 19 notifiable cases, Jev confirmed 17 and
sent the other two, `B20` HIV and typhoid `A01.0`, to review. None was dismissed outright. Those two still
count as misses in the recall figure, and the rules caught HIV by code. It's one run on a small set, so
a low score from Jev shouldn't close a case on its own yet.

**Confidence isn't reliable everywhere.** Thresholds only work if confidence means something. On
notifiable disease, all 17 decisions in the 0.8–1.0 bucket were correct. On quality scoring, the same
bucket averaged 0.82 confidence and was right 69% of the time. The quality threshold is less trustworthy
than it looks.

**Latency missed by an order of magnitude.** I targeted a p50 under 30 ms. Live p50 was about 235 ms
for routing and notifiable, and 470 ms for quality, where a Patient takes two calls. These are
client-side round trips from my machine, so they include the network, and I haven't separated model
time from that. Either way, the "tens of milliseconds" premise isn't proven by this data.

**Cost was close to nothing.** The full run used 146,760 tokens for about $0.006 at $42 per billion.
That's roughly $0.03 per 1,000 fixtures: triple my $0.01 target, and still negligible.

## How far to trust these numbers

- All data is synthetic. No real patient records were used.
- No human has approved the labels yet. 124 are pending review, and the other 80 are correct by
  construction because a generator produced them. Treat every accuracy here as provisional.
- The hard sets are small: 9 quality fixtures, 5 Bundles and 14 Conditions.
- This isn't a held-out test. I fixed the bug after seeing these same fixtures fail, so the 0.935 needs
  confirming on data the system hasn't seen.
- Results shift between runs. Quality scoring went from 0.676 to 0.648 between my two runs, on records
  the fix didn't touch, so small differences here mean little.
- The rules are a simple baseline, not a tuned production system.
- This is a proof of concept. It isn't connected to any production system, and it isn't a clinical
  decision support product.

## Where this could work in real life

None of this runs in production, and none of it has been tested on real records. These are the settings
the prototype was designed around, with what the current evidence says about each one.

### A provincial health data hub

Clinics across a province push FHIR R4 data to a shared hub for analytics and surveillance. Records
from different systems can all be valid and still vary widely in quality. Today someone finds the bad
ones later, in a report that looks wrong.

With a quality gate at the door, weak records go to a data steward before they reach analytics, and
each clinic could see which of its records were held and why.

**Evidence:** promising, but not ready to run unattended. Of 45 records that needed review, Jev let 15
through and the rules let 32 through. But Jev also held 10 of 26 good records, where the rules held none,
and its high confidence on quality isn't reliable. The safest first use is a dashboard that only
reports scores, with nothing blocked.

### Public health surveillance

A hospital records a suspected case of a notifiable disease, like dengue or tuberculosis. Reporting
depends on someone noticing and filing it, and the health office hears about it later than it should.

The decision layer would watch incoming Conditions and put likely cases in front of a surveillance
officer, with a draft FHIR Flag and an audit trail ready. It would handle the awkward cases that code
lookups can't, like a refuted diagnosis or a disease coded only in SNOMED.

**Evidence:** this is the strongest fit, as an extra safety net. All 17 high-confidence decisions were
correct, so those cases could go to the top of the officer's queue, and the two it didn't confirm still
reached the review lane. It can't replace existing reporting on the strength of one synthetic benchmark.
A person should confirm every report before it's sent, at least until this has been tested on real
records.

### Routing Bundles from many sources

A national or provincial platform receives Bundles from many vendors, and each type needs its own
processing pipeline.

**Evidence:** the weakest case. Rules were right on 12 Bundles that Jev got wrong, and the reverse
happened only once. Use rules here. If a model has a role, it's as a second opinion, sending
disagreements to a person.

### Ideas I haven't built

The same pattern could suit two other jobs, and I have no measurements for either:

- **Alert fatigue:** deciding whether a CDS Hooks alert should be shown, suppressed or escalated, so
  clinicians see fewer noisy alerts.
- **Duplicate patients:** deciding whether two Patient records from different facilities are the same
  person. A wrong merge is hard to undo, so a person would need to approve merges.

### What a real deployment would need

- Evaluation on real, de-identified records, with labels reviewed by clinicians.
- A privacy and legal review. Flattening limits what's sent, but it doesn't remove everything: the
  Patient state still includes the family name, and real data would go to a third-party API unless the
  model is hosted locally.
- Approval from the health authority before any automated step touches official reporting.
- Monitoring for drift, so a change in a clinic's data shows up before confidence quietly stops meaning
  what it did.

## What I'd conclude

Keep your validator. Then split the remaining decisions by what they need:

- **Clear structural logic**, like routing a Bundle by resource type: use rules. They were more accurate
  here and they're free.
- **Judgment that depends on several fields**, like whether this coded disease is actually a confirmed
  case: a model like Jev is worth testing, with the rules kept alongside as a check.
- **Anything high-stakes where the model is unsure:** send it to a person.

The design I'd keep is the shape of the system: conformance gate, typed decision, explicit threshold,
human review lane, and a benchmark that can prove you wrong. It did that to me on routing and latency.

Next, a human needs to review the labels. After that I'd measure latency from a closer network location
and try sending low-confidence cases to an LLM before they reach a person.

---

<!--
Open items before publishing (remove this block):
1. Host the video and replace the VIDEO comment above. GitHub and dev.to may need an MP4 or a link.
2. Budi: approve the labels, or keep the "provisional" wording.
3. Confirm the vendor's spelling: the PRD says "Typesafe AI", AGENTS.md says "TypeSafe".
4. Check with Typesafe AI whether publishing these results and $42/billion pricing is allowed.
5. Rule accuracies depend on baselines being unchanged; rerun numbers if the labels change.
-->
