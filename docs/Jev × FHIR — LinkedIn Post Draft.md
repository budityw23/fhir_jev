A FHIR record can be valid and still be wrong to act on.

A Patient can pass validation with a 15-digit national ID (It should be 16-Digit). A Condition can be well-formed, coded as dengue, and marked "refuted".

Validation tells you a record meets the spec. It doesn't tell you what to do next.

So I built Jev × FHIR, a proof of concept that adds a decision layer on top of FHIR data. It uses TypeSafe AI's Jev model to score record quality, route data, and flag notifiable diseases. When it's unsure, a person decides.

I tested the live model against handwritten rules on 204 synthetic records:

- Notifiable disease: 94% vs 68%
- Bundle routing: 95% vs 92%
- Quality scoring: 66% vs 55%

It didn't start there. My first run scored 84% on disease and lost routing to the rules, 81% vs 92%.

Both problems were mine. Free-text diagnoses were never reaching the model, and I was asking the wrong routing question. After fixing those on the same test set, disease reached 94% and routing reached 95%.

It still misses my speed target and some accuracy targets, the labels are provisional, and these results need confirming on new data.

My takeaway: validate first, check exactly what the model receives, keep rules as a baseline, and keep a person on the uncertain cases.

Where would you put a decision layer in your FHIR pipeline?

#FHIR #HealthIT #HealthcareAI #Interoperability

---

Not part of the post:
- Final numbers are from live report bench_20261101T054220Z. The first-run numbers are from bench_20261031T150439Z and bench_20261101T001036Z.
- The current videos show the older results, including "Rules win routing". Re-record before attaching one.
- Replace [article link] once the article is published.
