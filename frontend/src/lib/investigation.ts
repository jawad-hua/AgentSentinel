export interface AnalysisStage {
  id: number;
  stage: string;
  status: string;
  started_at: string;
  finished_at: string | null;
  output: Record<string, unknown> | null;
}
export interface Analysis {
  can_request_assessment: boolean;
  review_of: number | null;
  id: number;
  execution_id: string;
  status: string;
  stage: string | null;
  trigger: string;
  model: string;
  created_at: string;
  finished_at: string | null;
  newer_failure_observed: boolean;
  error: string | null;
  evidence: {
    operator_review_of?: number;
    revision_matches: boolean;
    execution_revision: string;
    current_revision: string;
    limits: string[];
    facts: { id: string; kind: string; value: unknown }[];
  } | null;
  policy: {
    decision: string;
    risk_level: string;
    reasons: string[];
    changes: { node: string; field: string; before: unknown; after: unknown }[];
    confidence: {
      label: string;
      supported_hypotheses: number;
      total_hypotheses: number;
      evidence_coverage_percent: number;
      meaning: string;
    };
    validation_scope: string;
  } | null;
  stages: AnalysisStage[];
}
export interface InvestigationData {
  items: Analysis[];
  enabled: boolean;
  configured: boolean;
  automatic_new_incidents: boolean;
  daily_limit: number;
  history_limit: number;
}
