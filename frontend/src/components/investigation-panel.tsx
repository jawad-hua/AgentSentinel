import type { InvestigationData } from "@/lib/investigation";
import { displayTime } from "@/lib/monitoring";
import { AnalyzeButton } from "@/components/analyze-button";

function Value({ value }: { value: unknown }) {
  if (value === null) return <span>Not identified</span>;
  if (typeof value === "boolean") return <span>{value ? "Yes" : "No"}</span>;
  if (Array.isArray(value))
    return value.length ? (
      <ul>
        {value.map((item, i) => (
          <li key={i}>
            <Value value={item} />
          </li>
        ))}
      </ul>
    ) : (
      <span>None reported</span>
    );
  if (typeof value === "object")
    return (
      <dl className="analysis-values">
        {Object.entries(value as Record<string, unknown>).map(([key, item]) => (
          <div key={key}>
            <dt>{key.replaceAll("_", " ")}</dt>
            <dd>
              <Value value={item} />
            </dd>
          </div>
        ))}
      </dl>
    );
  return <span>{String(value)}</span>;
}

export function InvestigationPanel({
  id,
  data,
}: {
  id: number;
  data: InvestigationData | null;
}) {
  if (!data)
    return (
      <section className="panel evidence-panel">
        <h2>Investigation unavailable</h2>
        <p>
          Could not read investigation state. Refresh after checking the service
          connection.
        </p>
      </section>
    );
  const latest = data.items[0];
  const active = latest && ["queued", "running"].includes(latest.status);
  return (
    <section className="investigation-section">
      <div className="panel evidence-panel">
        <span className="eyebrow">AI INVESTIGATION</span>
        <h2>
          {latest ? latest.status.replaceAll("_", " ") : "Ready to investigate"}
        </h2>
        <p>
          Five bounded analysis stages. Only minimized execution facts are sent
          to Groq. Proposals cannot modify workflows.
        </p>
        {!data.enabled && (
          <p className="analysis-warning">
            Analysis is disabled in server configuration.
          </p>
        )}
        {!data.configured && (
          <p className="analysis-warning">
            Configure Groq before requesting analysis.
          </p>
        )}
        {latest?.can_request_assessment && (
          <div className="analysis-warning">
            <p>
              Triage stopped deeper analysis. After reviewing its reason, you
              can request a read-only repair assessment. The original decision
              remains in the audit trail; validation and approval are still
              required for any change.
            </p>
            <AnalyzeButton
              id={id}
              again={false}
              reviewOf={latest.id}
              disabled={!data.enabled || !data.configured || Boolean(active)}
            />
          </div>
        )}
        <AnalyzeButton
          id={id}
          disabled={!data.enabled || !data.configured || Boolean(active)}
          again={Boolean(latest)}
        />
        <small>
          {data.enabled && data.configured && data.automatic_new_incidents
            ? "New incidents are investigated automatically while the service is running."
            : "Analysis starts on operator request."}{" "}
          Budget: {data.daily_limit} investigations per rolling 24 hours.
        </small>
        {!latest && <p>No agent has analyzed this incident yet.</p>}
      </div>
      {data.items.map((run, index) => (
        <details
          className="panel investigation-run"
          key={run.id}
          open={index === 0}
        >
          <summary>
            Investigation #{run.id} · {run.status.replaceAll("_", " ")} ·
            execution {run.execution_id}
          </summary>
          <p className="analysis-meta">
            {displayTime(run.created_at)} · {run.model} · {run.trigger}
          </p>
          {run.review_of && (
            <p className="analysis-meta">
              Operator-requested assessment of investigation #
              {run.review_of}. Original triage is referenced
              unchanged; it was not run again.
            </p>
          )}
          {run.error && (
            <p role="alert" className="analysis-warning">
              {run.error}
            </p>
          )}
          {run.newer_failure_observed && (
            <p className="analysis-warning">
              A newer failed execution exists. This analysis refers only to
              execution {run.execution_id}.
            </p>
          )}
          <div className="agent-stages" aria-label="Persisted agent progress">
            {["triage", "diagnosis", "fix", "validator", "risk"].map(
              (stage) => {
                const agent = run.stages.find((item) => item.stage === stage);
                return (
                  <div
                    key={stage}
                    className={`agent-stage ${agent?.status || "idle"}`}
                  >
                    <strong>{stage}</strong>
                    <span>
                      {agent?.status ||
                        (stage === "triage" && run.review_of
                          ? `Referenced from #${run.review_of}`
                          : "Not started")}
                    </span>
                  </div>
                );
              },
            )}
          </div>
          {run.status === "queued" && <p>Waiting for the analysis worker.</p>}
          {run.status === "running" && run.stage === "evidence" && (
            <p>Collecting execution evidence…</p>
          )}
          {run.evidence && (
            <details className="analysis-evidence">
              <summary>Observed evidence sent for analysis</summary>
              <p>
                {run.evidence.revision_matches
                  ? "Execution and current configuration fingerprints match."
                  : "Configuration has changed since the failed execution. Repair proposals will be blocked."}
              </p>
              <p>
                Node aliases refer to zero-based positions in the saved
                execution workflow. Raw node names and payloads are excluded.
              </p>
              <ul>
                {run.evidence.limits.map((item) => (
                  <li key={item}>{item}</li>
                ))}
              </ul>
              {run.evidence.facts.map((fact) => (
                <div className="fact" key={fact.id}>
                  <strong>
                    {fact.id} · {fact.kind.replaceAll("_", " ")}
                  </strong>
                  <Value value={fact.value} />
                </div>
              ))}
            </details>
          )}
          <div className="analysis-cards">
            {run.stages
              .filter((stage) => stage.output)
              .map((stage) => (
                <article key={stage.id} className="analysis-card">
                  <span className="eyebrow">
                    AI INTERPRETATION · {stage.stage}
                  </span>
                  <Value value={stage.output} />
                </article>
              ))}
          </div>
          {run.policy && (
            <div className="policy-result">
              <span className="eyebrow">DETERMINISTIC POLICY</span>
              <h3>{run.policy.decision.replaceAll("_", " ")}</h3>
              <p>
                Risk: {run.policy.risk_level}. This is the analysis-time
                decision. See controlled remediation for current approval and
                execution state.
              </p>
              <ul>
                {run.policy.reasons.map((reason) => (
                  <li key={reason}>{reason}</li>
                ))}
              </ul>
              <h3>{run.policy.confidence.label}</h3>
              <p>
                Evidence coverage:{" "}
                {run.policy.confidence.evidence_coverage_percent}% (
                {run.policy.confidence.supported_hypotheses}/
                {run.policy.confidence.total_hypotheses} hypotheses).
              </p>
              <small>{run.policy.confidence.meaning}</small>
              {run.policy.changes.length > 0 && (
                <div className="diff-scroll">
                  <table className="proposal-diff">
                    <caption>Analysis-time proposed changes</caption>
                    <thead>
                      <tr>
                        <th>Node</th>
                        <th>Field</th>
                        <th>Before</th>
                        <th>After</th>
                      </tr>
                    </thead>
                    <tbody>
                      {run.policy.changes.map((change, i) => (
                        <tr key={i}>
                          <td>{change.node}</td>
                          <td>{change.field}</td>
                          <td>{JSON.stringify(change.before)}</td>
                          <td>{JSON.stringify(change.after)}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
              <p>{run.policy.validation_scope}</p>
            </div>
          )}
        </details>
      ))}
      {data.items.length > 0 && (
        <small>
          Showing the latest {data.history_limit} investigations. Earlier
          records remain in the audit database.
        </small>
      )}
    </section>
  );
}
