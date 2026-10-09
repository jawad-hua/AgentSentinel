import type { Incident, TimelineEvent } from "./monitoring";
export interface GraphNode {
  id: string;
  status: string;
}
export interface WarRoom {
  at: string;
  writes_paused: boolean;
  configured_kill_switch: boolean;
  monitoring_enabled: boolean;
  metrics: {
    monitored_workflows: number;
    incidents: number;
    open_incidents: number;
    diagnoses: number;
    repair_attempts: number;
    healed: number;
    failed_repairs: number;
    rollbacks: number;
    mean_detection_seconds: number | null;
    mean_repair_seconds: number | null;
    detection_samples: number;
    repair_samples: number;
  };
  focus: Incident | null;
  graph: GraphNode[];
  events: (TimelineEvent & {
    incident_id: number | null;
    workflow_id: string | null;
  })[];
  recent_repairs: {
    id: number;
    incident_id: number;
    status: string;
    finished_at: string | null;
  }[];
}
export interface ChaosData {
  enabled: boolean;
  targets: {
    id: string;
    name: string;
    designated: boolean;
    mode: string;
    session_id: number | null;
    expires_at: string | null;
  }[];
  sessions: {
    id: number;
    workflow_id: string;
    mode: string;
    created_at: string;
    expires_at: string;
    stopped_at: string | null;
    incident_ids: number[];
    attempts: {
      execution_id: string;
      attempt: number;
      http_status: number;
      at: string;
    }[];
  }[];
}
