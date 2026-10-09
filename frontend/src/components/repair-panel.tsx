import type { RepairData } from "@/lib/repairs";
import type { InvestigationData } from "@/lib/investigation";
import { displayTime } from "@/lib/monitoring";
import { RepairControls } from "@/components/repair-controls";

export function RepairPanel({
  data,
  analysis,
}: {
  data: RepairData | null;
  analysis: InvestigationData | null;
}) {
  if (!data)
    return (
      <section className="panel evidence-panel">
        <h2>Repair controls unavailable</h2>
        <p>Could not read persisted repair state.</p>
      </section>
    );
  const latest = analysis?.items[0];
  const eligible =
    latest?.status === "review_required" &&
    !data.items.some((r) => r.investigation_id === latest.id);
  return (
    <section className="repair-section">
      <div className="panel evidence-panel">
        <span className="eyebrow">CONTROLLED REMEDIATION</span>
        <h2>Review before change</h2>
        <p>
          Encrypted snapshots, revision-bound approval and actual execution
          verification. Automatic replay is disabled; a prepared repair includes
          a manual verification plan.
        </p>
        <div className="repair-status">
          <span className={`pill ${data.paused ? "warning" : "neutral"}`}>
            {data.paused ? "Writes paused" : "Approval required"}
          </span>
        </div>
        {!data.enabled && <p>Repairs are disabled in server configuration.</p>}
        {!data.designated && (
          <p>This workflow is not designated for repairs.</p>
        )}
        {!data.configured && (
          <p>
            Snapshot encryption and a separate write credential are required.
          </p>
        )}
        {eligible ? (
          <RepairControls
            mode="prepare"
            id={latest.id}
            disabled={!data.enabled || !data.designated || !data.configured}
          />
        ) : (
          <p>
            No new eligible proposal is available. Blocked investigations cannot
            be approved.
          </p>
        )}
        <RepairControls
          mode={data.paused ? "resume" : "pause"}
          disabled={data.paused && data.configured_kill_switch}
        />
        {data.configured_kill_switch && (
          <small>
            The configured kill switch is engaged. Runtime controls cannot
            override it.
          </small>
        )}
      </div>
      {data.items.map((row) => (
        <article key={row.id} className="panel evidence-panel repair-record">
          <span className="eyebrow">
            REPAIR #{row.id} · INVESTIGATION #{row.investigation_id}
          </span>
          <h3>{row.status.replaceAll("_", " ")}</h3>
          <p>
            Approval: {row.approval}. Risk: {row.verification.risk}.{" "}
            {row.snapshot_saved
              ? "Encrypted snapshot retained."
              : "Snapshot unavailable."}
          </p>
          {row.message && <p className="analysis-warning">{row.message}</p>}
          <div className="diff-scroll">
            <table className="proposal-diff">
              <caption>Revision-bound repair diff</caption>
              <thead>
                <tr>
                  <th>Node</th>
                  <th>Field</th>
                  <th>Before</th>
                  <th>After</th>
                </tr>
              </thead>
              <tbody>
                {row.changes.map((c) => (
                  <tr key={c.node + c.field}>
                    <td>{c.node}</td>
                    <td>{c.field}</td>
                    <td>{String(c.before)}</td>
                    <td>{String(c.after)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <details>
            <summary>Revision fingerprints</summary>
            <p className="revision-hash">Before: {row.before_hash}</p>
            <p className="revision-hash">After: {row.after_hash}</p>
          </details>
          <p>
            {row.verification.strategy}. Requires{" "}
            {row.verification.required_successes} successful executions and at
            least {row.verification.minimum_window_seconds} seconds of
            observation.
          </p>
          <p>
            Verified execution IDs:{" "}
            {row.verification.success_ids.join(", ") || "None yet"}. Failed
            verification IDs:{" "}
            {row.verification.failed_ids.join(", ") || "None observed"}.
          </p>
          <p>
            Approval expires: {displayTime(row.expires_at)}.{" "}
            {row.deadline && (
              <>Verification deadline: {displayTime(row.deadline)}.</>
            )}
          </p>
          {row.status === "verifying" && (
            <p className="analysis-warning">
              Reload the saved workflow in n8n and run it twice using Execute
              workflow. Avoid pinned data or partial node runs. A failed
              execution or missing recovery by the deadline triggers conditional
              rollback.
            </p>
          )}
          {row.status === "awaiting_approval" && (
            <RepairControls
              mode="decision"
              id={row.id}
              digest={row.digest}
              disabled={
                data.paused ||
                !data.enabled ||
                !data.designated ||
                !data.configured
              }
            />
          )}
          {row.status === "escalated" && row.holds_workflow && (
            <RepairControls mode="reconcile" id={row.id} />
          )}
          {row.finished_at && (
            <small>
              Finished {displayTime(row.finished_at)}.{" "}
              {row.status === "healed"
                ? "Recovery evidence covers the recorded observation window."
                : row.status === "rolled_back"
                  ? "Original configuration restored; this is not a healed outcome."
                  : "See the recorded outcome above."}
            </small>
          )}
        </article>
      ))}
    </section>
  );
}
