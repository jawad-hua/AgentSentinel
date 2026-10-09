"use client";
import { useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import type { ChaosData } from "@/lib/warroom";
import { displayTime } from "@/lib/monitoring";
export function ChaosPanel({ data }: { data: ChaosData | null }) {
  const router = useRouter();
  const [chosen, setChosen] = useState("");
  const [baseline, setBaseline] = useState("");
  const [ack, setAck] = useState(false);
  const [pending, setPending] = useState(false);
  const [message, setMessage] = useState("");
  const target = data?.targets.find((t) => t.id === chosen);
  async function act(action: string) {
    setPending(true);
    setMessage("");
    try {
      const r = await fetch("/api/chaos", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          action,
          workflow_id: chosen,
          baseline_execution: baseline,
          acknowledged: ack,
        }),
      });
      const result = await r.json();
      if (!r.ok) throw new Error(result.error || "Chaos action failed");
      setMessage(
        action === "designate"
          ? "Designated. Run one full healthy execution in n8n, then enter its ID."
          : action === "stop"
            ? "Fault stopped. Incident outcomes remain in the audit trail."
            : "Fault armed. Run the full saved workflow in n8n, then open its detected incident below.",
      );
      router.refresh();
    } catch (e) {
      setMessage(e instanceof Error ? e.message : "Request failed");
    } finally {
      setPending(false);
    }
  }
  return (
    <section className="panel chaos-panel" id="chaos">
      <div className="section-heading">
        <div>
          <span className="eyebrow">CONTROLLED EXPERIMENT</span>
          <h2>Chaos Mode</h2>
        </div>
        <span className={`pill ${data?.enabled ? "warning" : "neutral"}`}>
          {data ? (data.enabled ? "OPTED IN" : "DISABLED") : "UNAVAILABLE"}
        </span>
      </div>
      <p>
        Inject a real HTTP failure into an explicitly designated local test
        workflow. Diagnosis, approval and recovery use the normal incident
        pipeline.
      </p>
      {!data ? (
        <p role="alert">Chaos state could not be loaded.</p>
      ) : (
        <>
          {!data.targets.length ? (
            <div className="empty-state">
              No eligible test workflow. Configure the Chaos allowlist, sync the
              catalog and enable monitoring in Operations.
            </div>
          ) : (
            <>
              <label>
                Designated test workflow
                <select
                  value={chosen}
                  onChange={(e) => {
                    setChosen(e.target.value);
                    setAck(false);
                    setBaseline("");
                  }}
                >
                  <option value="">Select a test workflow</option>
                  {data.targets.map((t) => (
                    <option key={t.id} value={t.id}>
                      {t.name}
                    </option>
                  ))}
                </select>
              </label>
              {target && (
                <div className="chaos-current">
                  <strong>
                    {target.designated
                      ? `Probe mode: ${target.mode}`
                      : "Designation required"}
                  </strong>
                  {target.expires_at && (
                    <p>
                      Expires {displayTime(target.expires_at)}. Expiry returns
                      an error, never apparent recovery.
                    </p>
                  )}
                </div>
              )}
              <label>
                Healthy baseline execution ID
                <input
                  value={baseline}
                  onChange={(e) => setBaseline(e.target.value)}
                  maxLength={128}
                  placeholder="From your full n8n execution"
                />
              </label>
              <label className="ack-row">
                <input
                  type="checkbox"
                  checked={ack}
                  onChange={(e) => setAck(e.target.checked)}
                />
                This is an unpublished test-only workflow under my exclusive
                control. I authorize this fault experiment, not a repair.
              </label>
              <div className="chaos-actions">
                <button
                  className="button"
                  disabled={
                    pending ||
                    !ack ||
                    !target ||
                    target.designated ||
                    !data.enabled
                  }
                  onClick={() => act("designate")}
                >
                  Designate test workflow
                </button>
                <button
                  className="button"
                  disabled={
                    pending ||
                    !ack ||
                    !target?.designated ||
                    !!target?.session_id ||
                    !baseline ||
                    !data.enabled
                  }
                  onClick={() => act("transient")}
                >
                  Arm transient fault
                </button>
                <button
                  className="button"
                  disabled={
                    pending ||
                    !ack ||
                    !target?.designated ||
                    !!target?.session_id ||
                    !baseline ||
                    !data.enabled
                  }
                  onClick={() => act("persistent")}
                >
                  Arm persistent fault
                </button>
                <button
                  className="button"
                  disabled={pending || !ack || !target?.session_id}
                  onClick={() => act("stop")}
                >
                  Stop fault
                </button>
              </div>
              <p className="action-message" role="status">
                {pending ? "Checking real configuration…" : message}
              </p>
            </>
          )}
          <details>
            <summary>How the experiment works</summary>
            <ol className="instructions">
              <li>
                Designate the documented local probe workflow and run a full
                healthy baseline in n8n.
              </li>
              <li>
                Enter that execution ID and arm a fault. Transient returns 503
                on the first request per execution; persistent fails every
                attempt.
              </li>
              <li>
                Run the full workflow. Open the detected incident, inspect
                analysis and approve only an eligible repair.
              </li>
              <li>
                Keep the fault mode unchanged during repair verification. Run
                the patched workflow when prompted. Actual successful executions
                heal; failed verification triggers conditional rollback.
              </li>
              <li>
                After the repair finishes, stop the fault. A new experiment
                needs a fresh healthy baseline. Never edit a workflow during an
                active repair.
              </li>
            </ol>
          </details>
          <div className="chaos-history">
            {data.sessions.length ? (
              data.sessions.map((s) => (
                <details key={s.id}>
                  <summary>
                    Experiment #{s.id} · {s.mode} ·{" "}
                    {s.stopped_at ? "stopped" : "armed / expiry applies"}
                  </summary>
                  <p>{displayTime(s.created_at)}</p>
                  {s.incident_ids.map((id) => (
                    <Link
                      className="text-link"
                      href={`/incidents/${id}`}
                      key={id}
                    >
                      Open incident #{id} →{" "}
                    </Link>
                  ))}
                  {!s.attempts.length ? (
                    <p>No probe requests recorded. Run the workflow in n8n.</p>
                  ) : (
                    <div className="table-scroll">
                      <table>
                        <caption>
                          Latest 30 actual probe responses; workflow outcomes
                          are verified separately.
                        </caption>
                        <thead>
                          <tr>
                            <th>Execution</th>
                            <th>Attempt</th>
                            <th>HTTP</th>
                            <th>Observed at</th>
                          </tr>
                        </thead>
                        <tbody>
                          {s.attempts.map((a) => (
                            <tr key={`${a.execution_id}-${a.attempt}`}>
                              <td>{a.execution_id}</td>
                              <td>{a.attempt}</td>
                              <td>{a.http_status}</td>
                              <td>{displayTime(a.at)}</td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  )}
                </details>
              ))
            ) : (
              <p>No experiments recorded.</p>
            )}
          </div>
        </>
      )}
    </section>
  );
}
