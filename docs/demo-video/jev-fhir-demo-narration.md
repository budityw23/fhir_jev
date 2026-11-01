# Jev × FHIR — Demo Narration

English narration aligned to the existing 119.48-second captioned video.
Voice: Microsoft Edge `en-US-GuyNeural` (AI-generated).
Pronunciation: FHIR is spoken as “fire”; NIK is described as the national identifier.

| Time | Scene | Narration |
| --- | --- | --- |
| 00:00.50–00:07.00 | Introduction | Jev and FHIR. A decision layer for healthcare data. This walkthrough uses mock responses. |
| 00:07.30–00:14.10 | Conformance versus decisions | FHIR conformance asks: is this resource valid? This project asks: what should happen next? |
| 00:14.50–00:23.10 | Typed state | Resources are flattened into typed state. Jev returns a decision and a confidence, rather than generated text. |
| 00:23.90–00:30.60 | Complete Patient | A complete Patient is scored and accepted. The middle panel shows exactly what Jev receives. |
| 00:31.30–00:38.90 | Invalid NIK | This resource also parses as FHIR. But its national identifier has fifteen digits instead of sixteen, so it needs review. |
| 00:41.60–00:45.50 | Quality threshold | Raise the threshold, and more records need human review. |
| 00:46.00–00:53.00 | Bundle routing | Next, bundle routing. The model selects a pipeline and shows probabilities for the possible categories. |
| 00:54.30–01:01.00 | Confidence floor | When confidence falls below the floor, the result becomes unknown, leaving the decision to a person. |
| 01:01.70–01:09.30 | Notifiable disease | For a notifiable disease, the demo creates a FHIR Flag for the health office, together with an audit event. |
| 01:10.30–01:17.10 | Text-only dengue | The mock misses this text-only dengue case. After a serializer fix, the live model catches it. |
| 01:17.60–01:28.30 | Streaming pipeline | In the streaming pipeline, each resource enters one of four lanes: automatically accepted, routed, flagged, or sent for human review. |
| 01:28.80–01:39.40 | Live benchmark results | These benchmark results come from a separate live run on two hundred and four synthetic fixtures. Jev beats the baseline rules on quality and disease detection. Rules win routing. |
| 01:39.80–01:46.40 | Latency and limitations | Median latency misses the thirty millisecond target. Labels and accuracy results remain provisional. |
| 01:46.90–01:56.90 | Closing | This is a proof of concept using synthetic data. Keep conformance checks first, add decisions on top, and send uncertain cases to people. |

The interactive scenes use mock Jev. The benchmark screen displays an existing live report; no live Jev calls were made to produce this narration.

Narrated output: `jev-fhir-demo-narrated.webm`. The original silent video is retained.
Separate narration track: `jev-fhir-demo-narration.wav`.
