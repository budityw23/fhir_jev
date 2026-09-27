import { useHealth } from "../../api/queries";
import { ApiError } from "../../api/client";
import { ErrorCard } from "./ErrorCard";

/** Show health status and a retry affordance when the service cannot be reached. */
export function HealthDot() {
  const health = useHealth();
  if (health.isError)
    return (
      <div className="health-wrap">
        {health.error instanceof ApiError && <ErrorCard error={health.error.body} />}
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
