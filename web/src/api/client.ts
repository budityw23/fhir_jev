import type { ErrorBody } from "./types";

/** An error returned by the API with its request correlation identifier. */
export class ApiError extends Error {
  constructor(
    public status: number,
    public body: ErrorBody,
    public requestId: string | null,
  ) {
    super(body.error);
    this.name = "ApiError";
  }
}

/** Metadata from the most recently completed API request. */
export interface LastRequest {
  requestId: string | null;
  durationMs: number | null;
  path: string;
}

const listeners = new Set<(request: LastRequest) => void>();
let lastRequest: LastRequest | null = null;

/** Subscribe to metadata for each API response. */
export function subscribeLastRequest(
  callback: (request: LastRequest) => void,
): () => void {
  listeners.add(callback);
  return () => listeners.delete(callback);
}

/** Return request metadata retained for app-lifetime observability. */
export function getLastRequest(): LastRequest | null {
  return lastRequest;
}

/** Make a JSON API request and raise ApiError for non-success responses. */
export async function api<T>(path: string, init: RequestInit = {}): Promise<T> {
  const response = await fetch(path, {
    ...init,
    headers: {
      Accept: "application/json",
      ...(init.body ? { "Content-Type": "application/json" } : {}),
      ...init.headers,
    },
  });
  const requestId = response.headers.get("X-Request-Id");
  const duration = response.headers.get("X-Request-Duration-Ms");
  const durationMs = duration === null ? null : Number(duration);
  const request = {
    requestId,
    durationMs: Number.isFinite(durationMs) ? durationMs : null,
    path,
  };
  lastRequest = request;
  listeners.forEach((listener) => listener(request));
  if (!response.ok) {
    let body: ErrorBody = {
      error: response.statusText || "request_failed",
      detail: null,
      request_id: requestId ?? "",
      timestamp: "",
    };
    try {
      body = (await response.json()) as ErrorBody;
    } catch {
      /* Preserve a useful fallback for non-JSON errors. */
    }
    throw new ApiError(response.status, body, requestId);
  }
  return response.json() as Promise<T>;
}

/** Make a text API request while retaining request metadata for the drawer. */
export async function apiText(path: string): Promise<string> {
  const response = await fetch(path);
  const duration = response.headers.get("X-Request-Duration-Ms");
  const durationMs = duration === null ? null : Number(duration);
  const request = {
    requestId: response.headers.get("X-Request-Id"),
    durationMs: Number.isFinite(durationMs) ? durationMs : null,
    path,
  };
  lastRequest = request;
  listeners.forEach((listener) => listener(request));
  if (!response.ok) {
    throw new Error(`Metrics request failed (${response.status})`);
  }
  return response.text();
}
