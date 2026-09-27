import { noulView } from "../../lib/noul";

export interface NoulMeterProps {
  pTrue: number;
  reviewBand: [number, number];
}

/** Plot P(true) and label its affirmative or negative answer consistently. */
export function NoulMeter({ pTrue, reviewBand }: NoulMeterProps) {
  const view = noulView(pTrue);
  const [reviewStart, confirmedStart] = reviewBand;
  return (
    <section aria-label="Noul probability">
      <strong>{view.label}</strong>
      <div className="noul-meter">
        <i className="not-band" style={{ width: `${reviewStart * 100}%` }} />
        <i
          className="review-band"
          style={{
            left: `${reviewStart * 100}%`,
            width: `${(confirmedStart - reviewStart) * 100}%`,
          }}
        />
        <i
          className="confirmed-band"
          style={{
            left: `${confirmedStart * 100}%`,
            width: `${(1 - confirmedStart) * 100}%`,
          }}
        />
        <b style={{ left: `${pTrue * 100}%` }} />
      </div>
    </section>
  );
}
