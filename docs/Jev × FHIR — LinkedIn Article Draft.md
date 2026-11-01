# A FHIR Record Can Be Valid and Still Be Wrong to Act On

A clinic sends a Patient record. The structure is correct, and the name and birth date are there. But the NIK, Indonesia's national ID number, has 15 digits instead of 16.

Another clinic sends a Condition coded as dengue. It's also well-formed. But its status says "refuted", which means the patient doesn't have dengue.

Both records can pass FHIR validation. Neither should be treated like a normal record.

That gap is what made me want to build this project.

## What I built

I built Jev × FHIR, a proof of concept that adds a decision layer on top of FHIR data. FHIR is the standard healthcare systems use to exchange data. Jev is a decision model from TypeSafe AI that returns a structured judgment and a confidence score, without generating text.

The system makes three decisions:

- **Quality:** is this record good enough to accept automatically?
- **Routing:** which pipeline should process this Bundle of records?
- **Notifiable disease:** does this condition need reporting to the health office?

## How it works

1. **Check the record.** It must parse as valid FHIR R4 before any decision is made.
2. **Flatten it.** The record becomes a small set of typed fields. The demo shows exactly what the model sees.
3. **Decide.** Jev returns a score, category or yes/no answer, with a confidence.
4. **Act.** Thresholds turn that answer into an action: accept it, route it, flag it, or send it to a person.

That last option is the part I care about most. The system is allowed to say "I'm not sure" and hand the case to a human.

## Why it matters

FHIR conformance asks: is this record valid?

A decision layer asks: what should we do with it?

Both matter, and this doesn't replace validation. In my system, validation comes first. But healthcare data pipelines are full of decisions that come after it: who should review this, where should it go, and does someone need to be told today?

Many teams handle those decisions with growing piles of rules, or by waiting for someone to notice. I wanted to know whether a fast model could do better, so I tested it.

## The results

I ran the live model against handwritten rules on 204 synthetic records. These are the accuracy results:

- **Notifiable disease:** Jev 94%, rules 68%
- **Bundle routing:** Jev 95%, rules 92%
- **Quality scoring:** Jev 66%, rules 55%

The model won all three in the final run, but it didn't start there. My first results were 84% on notifiable disease and 81% on routing, where the rules won. It also still misses several of the targets I set before starting.

**The first gain came from fixing my own bug.** While reviewing the demo, I noticed the system was dropping free-text diagnoses. A disease written only as "TB paru" reached the model as a blank. I added that one field and re-ran the benchmark: exactly three disease records changed, all of them those free-text cases, and accuracy rose to 94%.

**Jev was best at context.** On the hardest disease cases it scored 93% against 36% for the rules. It refused to confirm the refuted dengue case and sent it to a person, and it recognized diseases coded in SNOMED that an ICD-10 lookup can't see. A better rule set would close part of that gap.

**The second gain came from asking a better question.** Rules first beat Jev on routing, 92% to 81%. The misses had a clear pattern: Jev got 0 of 11 encounter Bundles right when they held three or more diagnoses. I had asked what a Bundle "primarily" contains, and the data had no direct signal for encounters. I added that signal and asked which pipeline should handle the Bundle instead. All 11 then routed correctly, and accuracy rose to 95%. Fourteen records improved and none got worse.

**Rules are still a strong baseline.** They scored 92% on routing with no model at all. Jev still gets five mixed Bundles wrong, three of them at 87% confidence or higher, so confidence alone doesn't catch every mistake.

**No real disease case was dismissed.** Of 19 notifiable cases, Jev confirmed 17 and sent the other two to human review. Every alert it raised was correct. That's the design working as intended, though it's one run on a small synthetic set.

**It missed my speed target by a wide margin.** I aimed for 30 ms. Typical response times were about 230 to 460 ms, including network time.

**The cost was tiny.** The whole benchmark cost less than one cent.

All of this comes with limits. The data is synthetic, the hard test sets are small, and no human has reviewed the labels yet. I also made both fixes after seeing these same records fail, so the 94% and 95% still need confirming on data the system hasn't seen. Results also shift between runs: quality scoring moved between 65% and 68%. Treat these numbers as provisional.

## Real-life cases

**Public health surveillance.** This is the strongest fit. Likely cases of a disease like dengue or tuberculosis could go to a surveillance officer sooner, with the report already drafted. It would be an extra safety net with a person confirming every report, and it wouldn't replace existing reporting.

**A provincial health data hub.** Clinics send data to a shared hub, and weak records could be held for review before they reach analytics. Jev let through 14 of 45 records that needed review, compared with 32 for the rules. But it also held back 10 of 26 good records, so I'd start with a dashboard that shows scores and blocks nothing.

**Routing data from many sources.** This went from my weakest case to a close one. Rules are simple and scored 92%, so I'd keep them as the default and use Jev as a second opinion, with disagreements going to a person.

## The potential

The result I care about isn't a model beating rules. It's a pattern:

- Validate first.
- Check exactly what the model receives.
- Use rules where the logic is clear.
- Use a model where the decision depends on context.
- Send uncertain, high-stakes cases to a person.
- Measure all of it, so the data can prove you wrong.

The same pattern could help reduce clinical alert fatigue, or flag possible duplicate patients across facilities. I haven't built or tested those, so they're still only ideas.

Before any of this could touch real care, it would need testing on real de-identified records, labels reviewed by clinicians, a privacy review, and approval from health authorities.

Next, I'm getting the labels reviewed by a person and testing on data the system hasn't seen.

If you work with FHIR or public health data, I'd like to know where you'd put a decision layer, or where you'd never allow one.

<!--
Before publishing (remove this block):
1. Convert the video to MP4 and add it near the "How it works" section.
2. LinkedIn articles don't render Markdown: reapply the headings and bold text in its editor.

Final numbers are from live report bench_20261101T054220Z. First-run numbers are from bench_20261031T150439Z and bench_20261101T001036Z.
-->
