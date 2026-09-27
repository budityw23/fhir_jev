import { useHealth } from "../../api/queries";

/** Show the configured deterministic mock or live Jev mode. */
export function ModeBadge() {
  const { data, isError } = useHealth();
  if (isError || !data)
    return (
      <span className="mode-badge mode-unknown" aria-label="Mode unavailable">
        ? MODE
      </span>
    );
  const mock = data.jev_client === "mock";
  const label = mock ? "MOCK" : `LIVE · ${data.jev_model ?? "unknown"}`;
  return (
    <span
      className={`mode-badge ${mock ? "mode-mock" : "mode-live"}`}
      title={
        mock
          ? "Deterministic offline client — decisions are rule-derived, latency is simulated."
          : undefined
      }
    >
      {mock ? "● " : "✓ "}
      {label}
    </span>
  );
}
