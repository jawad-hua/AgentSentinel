"use client";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState } from "react";
import type { Catalog, IncidentList, Workflow } from "@/lib/monitoring";
import { displayTime } from "@/lib/monitoring";
import { LiveUpdates } from "./live-updates";

async function action(body: unknown) {
  const response = await fetch("/api/monitor/actions", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  const result = await response.json();
  if (!response.ok) throw new Error(result.error || "Request failed");
  return result;
}
function WorkflowCard({
  row,
  monitoringEnabled,
}: {
  row: Workflow;
  monitoringEnabled: boolean;
}) {
  const router = useRouter();
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState("");
  async function save(config: unknown) {
    setBusy(true);
    setMessage("");
    try {
      await action({ action: "configure", id: row.id, config });
      setMessage("Configuration saved.");
      router.refresh();
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Save failed");
    } finally {
      setBusy(false);
    }
  }
  const config = {
    enabled: !row.enabled,
    require_output: row.require_output,
    expect_json: row.expect_json,
    contract_node: row.contract_node,
    json_field: row.json_field,
  };
  const label = !monitoringEnabled
    ? "STOPPED"
    : !row.available
      ? "UNAVAILABLE"
      : !row.enabled
        ? "PAUSED"
        : row.last_error
          ? "CHECK FAILED"
          : row.stale
            ? "AWAITING FRESH CHECK"
            : "WATCHING";
  return (
    <article className="panel workflow-card">
      <div className="workflow-top">
        <div>
          <h3>{row.name}</h3>
          <small>
            ID {row.id} · {row.active ? "Active in n8n" : "Inactive in n8n"}
          </small>
        </div>
        <span
          className={`pill ${row.enabled && !row.last_error && !row.stale ? "success" : "neutral"}`}
        >
          {label}
        </span>
      </div>
      <div className="workflow-observation">
        <span>Latest observed execution</span>
        <strong>
          {row.last_execution
            ? `${row.last_execution.status}${row.last_execution.has_findings ? " · findings detected" : ""}`
            : "No executions observed"}
        </strong>
        {row.last_execution && (
          <small>
            Execution {row.last_execution.id} ·{" "}
            {row.last_execution.duration_ms === null
              ? "Duration unavailable"
              : `${row.last_execution.duration_ms} ms`}{" "}
            ·{" "}
            {row.last_execution.evidence_available
              ? "Trace available"
              : "Trace unavailable"}
          </small>
        )}
      </div>
      <p className="poll-time">
        Last check: {displayTime(row.last_polled_at)}
        {row.backfill_pending ? " · history backfill pending" : ""}
      </p>
      {row.last_error && (
        <p role="alert" className="inline-error">
          {row.last_error}
        </p>
      )}
      <div className="workflow-controls">
        <button
          disabled={busy || !row.available}
          className="button secondary"
          onClick={() => save(config)}
        >
          {busy
            ? "Saving…"
            : row.enabled
              ? "Pause monitoring"
              : "Enable monitoring"}
        </button>
        <span>{row.incident_count} recorded incidents</span>
      </div>
      <details className="contract-settings">
        <summary>Output expectations</summary>
        <p>
          Optional. Checks apply only to recorded output from this exact node.
          Existing inspected executions are not re-evaluated.
        </p>
        <form
          onSubmit={(event) => {
            event.preventDefault();
            const data = new FormData(event.currentTarget);
            save({
              enabled: row.enabled,
              require_output: data.has("require_output"),
              expect_json: data.has("expect_json"),
              contract_node: String(data.get("node") || "").trim() || null,
              json_field: String(data.get("field") || "").trim() || null,
            });
          }}
        >
          <label>
            Exact node name
            <input
              name="node"
              maxLength={256}
              defaultValue={row.contract_node ?? ""}
            />
          </label>
          <label className="checkbox">
            <input
              name="require_output"
              type="checkbox"
              defaultChecked={row.require_output}
            />{" "}
            Require non-empty output
          </label>
          <label className="checkbox">
            <input
              name="expect_json"
              type="checkbox"
              defaultChecked={row.expect_json}
            />{" "}
            Require a JSON object or array
          </label>
          <label>
            JSON field path
            <input
              name="field"
              maxLength={256}
              defaultValue={row.json_field ?? ""}
            />
            <small>Dot-separated path inside each item’s JSON output.</small>
          </label>
          <button className="button secondary" disabled={busy}>
            Save expectations
          </button>
        </form>
      </details>
      <p role="status" className="check-result">
        {message}
      </p>
    </article>
  );
}
export function MonitoringPanel({
  catalog,
  incidents,
}: {
  catalog: Catalog | null;
  incidents: IncidentList | null;
}) {
  const router = useRouter();
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState("");
  async function run(name: "sync" | "poll") {
    setBusy(true);
    setMessage("");
    try {
      const result = await action({ action: name });
      setMessage(
        name === "sync"
          ? `${result.synced} workflows synced from n8n.`
          : "Execution check requested. Waiting for actual results.",
      );
      router.refresh();
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Request failed");
    } finally {
      setBusy(false);
    }
  }
  return (
    <section className="monitor-section" id="monitoring">
      <div className="section-heading">
        <div>
          <span className="eyebrow">EXECUTION WATCH</span>
          <h2>Monitored workflows</h2>
        </div>
        <LiveUpdates />
      </div>
      <div className="monitor-toolbar">
        <p>
          Choose which workflows to watch. Read-only checks
          {catalog
            ? ` run every ${catalog.poll_interval_seconds} seconds after each cycle`
            : ""}
          .
        </p>
        <div>
          <button
            className="button secondary"
            disabled={busy}
            onClick={() => run("sync")}
          >
            Sync from n8n
          </button>
          <button
            className="button secondary"
            disabled={busy || !catalog?.monitoring_enabled}
            onClick={() => run("poll")}
          >
            Check executions
          </button>
        </div>
      </div>
      <p className="action-result" role="status">
        {message}
      </p>
      {!catalog ? (
        <div role="alert" className="panel empty-state">
          Monitoring data is unavailable. Check the service and database
          migrations.
        </div>
      ) : (
        <>
          {!catalog.monitoring_enabled && (
            <div className="error-banner">
              Monitoring is disabled in server configuration.
            </div>
          )}
          {catalog.items.length === 0 ? (
            <div className="panel empty-state">
              <h3>No workflows synced</h3>
              <p>
                Connect n8n, then sync its workflow catalog. Monitoring is
                opt-in; syncing does not execute or modify workflows.
              </p>
            </div>
          ) : (
            <div className="workflow-grid">
              {catalog.items.map((row) => (
                <WorkflowCard
                  key={row.id}
                  row={row}
                  monitoringEnabled={catalog.monitoring_enabled}
                />
              ))}
            </div>
          )}
        </>
      )}
      <div className="section-heading incidents-heading" id="incidents">
        <h2>Detected incidents</h2>
        <Link href="/incidents">View all incidents →</Link>
      </div>
      {!incidents ? (
        <div className="panel empty-state">
          Incident records could not be loaded.
        </div>
      ) : incidents.items.length === 0 ? (
        <div className="panel empty-state">
          <h3>No incidents recorded</h3>
          <p>
            This does not establish workflow health. Only observed failures or
            supported anomalies create incidents.
          </p>
        </div>
      ) : (
        <div className="panel incident-list">
          {incidents.items.map((row) => (
            <Link
              key={row.id}
              href={`/incidents/${row.id}`}
              className="incident-row"
            >
              <span
                className={`pill ${row.severity === "high" ? "danger" : "warning"}`}
              >
                {row.severity}
              </span>
              <div>
                <strong>{row.summary}</strong>
                <small>
                  {row.workflow_name} · {row.node || "Workflow-level evidence"}
                </small>
              </div>
              <span className="occurrences">
                {row.occurrences} occurrence{row.occurrences === 1 ? "" : "s"}
              </span>
              <span aria-hidden="true">↗</span>
            </Link>
          ))}
        </div>
      )}
    </section>
  );
}
