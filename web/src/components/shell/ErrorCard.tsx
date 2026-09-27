import type { ErrorBody } from "../../api/types";

/** Render API errors with the request id needed for support correlation. */
export function ErrorCard({ error }: { error: ErrorBody }) {
  const copy = (): void => {
    void navigator.clipboard?.writeText(error.request_id);
  };
  return (
    <section className="error-card" role="alert">
      <strong>{error.error}</strong>
      {error.detail && <p>{error.detail}</p>}
      <p>
        request_id: <code>{error.request_id}</code>
      </p>
      <button type="button" onClick={copy}>
        copy request id
      </button>
    </section>
  );
}
