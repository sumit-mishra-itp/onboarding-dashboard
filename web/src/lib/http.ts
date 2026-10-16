/** The only place that talks to the backend. Services call this; components call services. */
export class ApiError extends Error {
  constructor(public status: number, message: string) {
    super(message);
  }
}

// Set by App: a 401 on any non-auth call means the session ended (expired, password changed, deactivated).
let onUnauthorized = () => {};
export const setUnauthorizedHandler = (fn: () => void) => {
  onUnauthorized = fn;
};

export async function http<T = unknown>(path: string, method = "GET", body?: unknown): Promise<T> {
  const res = await fetch(`/api${path}`, {
    method,
    headers: body !== undefined ? { "Content-Type": "application/json" } : undefined,
    body: body !== undefined ? JSON.stringify(body) : undefined,
  });
  if (res.status === 204) return undefined as T;
  const data = await res.json().catch(() => null);
  if (!res.ok) {
    if (res.status === 401 && !path.startsWith("/auth/")) onUnauthorized();
    const d = data?.detail;
    // FastAPI validation errors arrive as a list of {loc, msg}.
    const msg = Array.isArray(d) ? d.map((e) => `${e.loc.slice(1).join(".")}: ${e.msg}`).join("\n") : d ?? res.statusText;
    throw new ApiError(res.status, msg);
  }
  return data as T;
}
