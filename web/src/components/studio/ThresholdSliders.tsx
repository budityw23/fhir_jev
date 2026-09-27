import type { DemoModule, Thresholds } from "../../api/types";

export interface ThresholdSlidersProps {
  module: DemoModule;
  value: Thresholds;
  onChange: (value: Thresholds) => void;
}

/** Edit just the decision thresholds used by the selected module. */
export function ThresholdSliders({ module, value, onChange }: ThresholdSlidersProps) {
  const set = (key: keyof Thresholds, next: number) => {
    const updated = { ...value, [key]: next };
    if (key === "notifiable_review") {
      updated.notifiable_review = Math.min(next, value.notifiable_confirmed);
    }
    if (key === "notifiable_confirmed") {
      updated.notifiable_confirmed = Math.max(next, value.notifiable_review);
    }
    onChange(updated);
  };
  return (
    <section aria-label="Decision thresholds">
      <h4>Thresholds</h4>
      {module === "quality" && (
        <Slider
          label="Quality threshold"
          value={value.quality_threshold}
          min={0}
          max={100}
          step={1}
          onChange={(next) => set("quality_threshold", next)}
        />
      )}
      {module === "router" && (
        <Slider
          label="Route confidence minimum"
          value={value.route_confidence_minimum}
          min={0}
          max={1}
          step={0.01}
          onChange={(next) => set("route_confidence_minimum", next)}
        />
      )}
      {module === "notifiable" && (
        <>
          <Slider
            label="Notifiable review"
            value={value.notifiable_review}
            min={0}
            max={1}
            step={0.01}
            onChange={(next) => set("notifiable_review", next)}
          />
          <Slider
            label="Notifiable confirmed"
            value={value.notifiable_confirmed}
            min={0}
            max={1}
            step={0.01}
            onChange={(next) => set("notifiable_confirmed", next)}
          />
        </>
      )}
    </section>
  );
}

type SliderProps = {
  label: string;
  value: number;
  min: number;
  max: number;
  step: number;
  onChange: (value: number) => void;
};

function Slider({ label, value, min, max, step, onChange }: SliderProps) {
  return (
    <label className="slider-label">
      {label}: {value.toFixed(step < 1 ? 2 : 0)}
      <input
        type="range"
        aria-label={label}
        min={min}
        max={max}
        step={step}
        value={value}
        onChange={(event) => onChange(Number(event.target.value))}
      />
    </label>
  );
}
