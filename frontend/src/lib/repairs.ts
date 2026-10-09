export interface RepairRecord {
  id: number;
  investigation_id: number;
  status: string;
  approval: string;
  digest: string;
  before_hash: string;
  after_hash: string;
  created_at: string;
  expires_at: string;
  applied_at: string | null;
  deadline: string | null;
  finished_at: string | null;
  snapshot_saved: boolean;
  holds_workflow: boolean;
  message: string | null;
  changes: {
    node: string;
    field: string;
    before: boolean | number;
    after: boolean | number;
  }[];
  verification: {
    strategy: string;
    required_successes: number;
    minimum_window_seconds: number;
    timeout_seconds: number;
    success_ids: string[];
    failed_ids: string[];
    risk: string;
  };
}
export interface RepairData {
  items: RepairRecord[];
  enabled: boolean;
  designated: boolean;
  paused: boolean;
  configured: boolean;
  configured_kill_switch: boolean;
}
