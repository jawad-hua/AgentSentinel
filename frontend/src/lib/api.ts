import "server-only";

export interface SystemStatus {
  service: string;
  version: string;
  database: string;
  kill_switch: boolean;
  monitoring_enabled: boolean;
  repairs_enabled: boolean;
  monitored_workflows: number;
  incident_count: number;
  execution_count: number;
  integrations: { n8n: boolean; groq: boolean };
  heartbeat_count: number;
  last_heartbeat: string | null;
}

export async function api(path: string, method = "GET", body?: unknown) {
  const base = process.env.AGENTSENTINEL_API_URL;
  const token = process.env.ADMIN_API_TOKEN;
  if (!base || !token) throw new Error("Service connection is not configured.");
  const response = await fetch(`${base}${path}`, {
    method,
    headers: {
      Authorization: `Bearer ${token}`,
      "Content-Type": "application/json",
    },
    body: body === undefined ? undefined : JSON.stringify(body),
    cache: "no-store",
    signal: AbortSignal.timeout(55000),
    redirect: "error",
  });
  if (!response.ok) {
    const data = await response.json().catch(() => ({}));
    throw new Error(
      typeof data.detail === "string"
        ? data.detail
        : `Service request failed (${response.status}).`,
    );
  }
  return response.json();
}

export async function systemStatus(): Promise<SystemStatus> {
  return api("/api/v1/status");
}
