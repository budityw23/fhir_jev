import { useHealth } from "../../api/queries";

/** Show health status and a retry affordance when the service cannot be reached. */
export function HealthDot() {
  const health = useHealth();
  if (health.isError)
    return (
      <div className="health-wrap">
        <span className="health-dot health-down" role="status">
          ● Offline
        </span>
        <button type="button" onClick={() => void health.refetch()}>
          Retry connection
        </button>
      </div>
    );
  return (
    <span className="health-dot health-up" role="status">
      ● {health.isLoading ? "Checking" : "Healthy"}
    </span>
  );
}
