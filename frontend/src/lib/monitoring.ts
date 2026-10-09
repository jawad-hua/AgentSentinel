export interface Workflow {
  id: string;
  name: string;
  active: boolean;
  available: boolean;
  enabled: boolean;
  require_output: boolean;
  expect_json: boolean;
  contract_node: string | null;
  json_field: string | null;
  monitor_since: string | null;
  last_polled_at: string | null;
  last_error: string | null;
  stale: boolean;
  incident_count: number;
  backfill_pending: boolean;
  last_execution: {
    id: string;
    status: string;
    started_at: string | null;
    duration_ms: number | null;
    has_findings: boolean;
    evidence_available: boolean;
  } | null;
}
export interface Incident {
  id: number;
  workflow_id: string;
  workflow_name: string;
  kind: string;
  node: string | null;
  severity: string;
  status: string;
  summary: string;
  occurrences: number;
  first_execution_id: string;
  last_execution_id: string;
  detected_at: string;
  last_seen_at: string;
  evidence: Record<string, string | number>;
}
export interface TimelineEvent {
  id: number;
  kind: string;
  message: string;
  created_at: string;
}
export interface IncidentDetail extends Incident {
  timeline: TimelineEvent[];
  timeline_limit: number;
  occurrences_recent: {
    execution_id: string;
    evidence: Record<string, string | number>;
    observed_at: string;
  }[];
}
export interface Catalog {
  items: Workflow[];
  monitoring_enabled: boolean;
  poll_interval_seconds: number;
}
export interface IncidentList {
  items: Incident[];
  next_before: number | null;
}
export function displayTime(value: string | null) {
  return value
    ? new Date(value).toISOString().replace("T", " ").slice(0, 19) + " UTC"
    : "Not observed";
}
