A FHIR record can be valid and still be wrong to act on.

A Patient can pass validation with a 15-digit national ID. A Condition can be well-formed, coded as dengue, and marked "refuted".

Validation tells you a record meets the spec. It doesn't tell you what to do next.

So I built Jev × FHIR, a proof of concept that adds a decision layer on top of FHIR data. It uses TypeSafe AI's Jev model to score record quality, route data, and flag notifiable diseases. When it's unsure, a person decides.

I tested the live model against handwritten rules on 204 synthetic records:

- Notifiable disease: 94% vs 68%
- Quality scoring: 65% vs 55%
- Bundle routing: 81% vs 92% (rules won)

It also missed my speed target and most of my accuracy targets. The labels are still provisional.

The biggest jump came from fixing my own bug. Free-text diagnoses were never reaching the model. One added field took disease accuracy from 84% to 94% on the same test set.

My takeaway: validate first, use rules for clear logic, use a model where context matters, and keep a person on the uncertain cases.

The 2-minute demo is below, and the full write-up is here: [article link]

Where would you put a decision layer in your FHIR pipeline?

#FHIR #HealthIT #HealthcareAI #Interoperability

---

Not part of the post:
- All numbers are from live report bench_20261101T001036Z.
- Attach the video as MP4. Its interface runs on a mock model, and its Benchmarks page shows the live results.
- Replace [article link] once the article is published.
