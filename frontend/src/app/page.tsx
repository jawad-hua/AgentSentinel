import Link from "next/link";
import { api } from "@/lib/api";
import type { WarRoom, ChaosData } from "@/lib/warroom";
import type { Catalog } from "@/lib/monitoring";
import { displayTime } from "@/lib/monitoring";
import { AgentGraph } from "@/components/agent-graph";
import { ChaosPanel } from "@/components/chaos-panel";
import { LiveUpdates } from "@/components/live-updates";
import { RepairControls } from "@/components/repair-controls";
import { Refresh } from "@/components/refresh";
export const dynamic = "force-dynamic";
export default async function Home() {
  const [room, chaos, catalog] = await Promise.all([
    api("/api/v1/war-room").catch(() => null) as Promise<WarRoom | null>,
    api("/api/v1/chaos").catch(() => null) as Promise<ChaosData | null>,
    api("/api/v1/workflows").catch(() => null) as Promise<Catalog | null>,
  ]);
  const focus = room?.focus;
  const metrics = room?.metrics;
  return (
    <div className="app-shell war-room">
      <aside className="sidebar">
        <Link href="/" className="brand">
          <span className="brand-icon">S</span>AgentSentinel
        </Link>
        <div className="workspace">
          <span className="eyebrow">RELIABILITY WORKSPACE</span>
          <strong>Local operations</strong>
          <small>Evidence before action</small>
        </div>
        <nav aria-label="Main navigation">
          <Link href="/" className="nav-active">
            ◈ War Room
          </Link>
          <Link href="/incidents">◇ Incident register</Link>
          <a href="#chaos">◎ Chaos Mode</a>
          <Link href="/operations">⇄ Operations & controls</Link>
        </nav>
        <div className="sidebar-bottom">
          <span className="tiny-dot" />
          Bounded autonomy<small>Every action leaves evidence.</small>
        </div>
      </aside>
      <main>
        <header className="topbar">
          <span>
            Operations / <strong>War Room</strong>
          </span>
          <LiveUpdates />
        </header>
        <div className="content">
          <div className="page-heading">
            <div>
              <span className="eyebrow">AUTOMATION RELIABILITY</span>
              <h1>The agent War Room.</h1>
              <p>
                Follow the evidence. Review the decision. Verify the recovery.
              </p>
            </div>
            <Refresh />
          </div>
          {!room && (
            <div className="error-banner" role="alert">
              Operations state unavailable. Check the service and migrations.
            </div>
          )}
          <section className="panel command-center">
            <div>
              <span className="eyebrow">CURRENT INVESTIGATION FOCUS</span>
              <h2>
                {focus
                  ? focus.status.replaceAll("_", " ")
                  : room
                    ? "Waiting for evidence"
                    : "Unavailable"}
              </h2>
              <p>
                {focus
                  ? `${focus.workflow_name} · ${focus.kind.replaceAll("_", " ")} · execution ${focus.last_execution_id}`
                  : "Monitored executions and incident investigations will appear here."}
              </p>
            </div>
            {focus && (
              <Link className="button" href={`/incidents/${focus.id}`}>
                Investigate #{focus.id} →
              </Link>
            )}
            <div className="command-footer">
              <span>
                {room
                  ? room.monitoring_enabled
                    ? "Monitoring configured · freshness below"
                    : "Monitoring disabled"
                  : "Monitoring unknown"}
              </span>
              <Link href="/operations#safety">
                {room
                  ? room.writes_paused
                    ? "Repair writes paused"
                    : "Approval-gated writes"
                  : "Safety state unknown"}{" "}
                →
              </Link>
            </div>
          </section>
          <section
            className="war-metrics"
            aria-label="Persisted operational totals"
          >
            {[
              ["Monitored workflows", metrics?.monitored_workflows],
              ["Open incidents", metrics?.open_incidents],
              ["Verified repairs", metrics?.healed],
              ["Verified rollbacks", metrics?.rollbacks],
            ].map(([label, value]) => (
              <article className="panel metric" key={label}>
                <span>{label}</span>
                <strong>{value ?? "—"}</strong>
                <small>Persisted system state</small>
              </article>
            ))}
          </section>
          <section className="panel graph-panel">
            <div className="section-heading">
              <h2>Live agent pipeline</h2>
              <span>
                {focus ? `Incident #${focus.id}` : "No incident selected"}
              </span>
            </div>
            {room && <AgentGraph nodes={room.graph} />}
            <p>
              Stages activate only while their recorded work is running.
              Referenced triage is retained history. This view does not imply
              all workflows are healthy.
            </p>
          </section>
          <div className="war-columns">
            <section className="panel workflow-watch">
              <div className="section-heading">
                <h2>Workflow watch</h2>
                <Link href="/operations#monitoring">Manage →</Link>
              </div>
              {!catalog ? (
                <p>Workflow state unavailable.</p>
              ) : !catalog.items.some((w) => w.enabled) ? (
                <div className="empty-state">
                  No monitored workflows. Select workflows in Operations.
                </div>
              ) : (
                catalog.items
                  .filter((w) => w.enabled)
                  .map((w) => (
                    <article key={w.id} className="watch-row">
                      <div>
                        <strong>{w.name}</strong>
                        <small>
                          Last poll: {displayTime(w.last_polled_at)}
                        </small>
                      </div>
                      <span
                        className={`pill ${w.stale || w.last_error || !w.available || w.last_execution?.has_findings ? "warning" : "neutral"}`}
                      >
                        {w.stale
                          ? "STALE"
                          : w.last_error
                            ? "POLL ERROR"
                            : !w.available
                              ? "UNAVAILABLE"
                              : w.last_execution
                                ? w.last_execution.status
                                : "NO EXECUTIONS"}
                      </span>
                    </article>
                  ))
              )}
            </section>
            <section className="panel outcome-panel">
              <h2>Repair outcomes</h2>
              {room?.recent_repairs.length ? (
                room.recent_repairs.map((r) => (
                  <Link
                    href={`/incidents/${r.incident_id}`}
                    className="watch-row"
                    key={r.id}
                  >
                    <strong>Repair #{r.id}</strong>
                    <span
                      className={`pill ${r.status === "healed" ? "success" : "neutral"}`}
                    >
                      {r.status.replaceAll("_", " ")}
                    </span>
                  </Link>
                ))
              ) : (
                <div className="empty-state">No repair records yet.</div>
              )}
              <p>
                Healed outcomes cover their verification window; they do not
                establish current workflow health.
              </p>
            </section>
          </div>
          <section className="panel graph-panel" id="safety">
            <h2>Repair safety</h2>
            <p>
              Pausing stops both repair and rollback writes. Keep writes
              available during approved verification.
            </p>
            {room && (
              <RepairControls
                mode={room.writes_paused ? "resume" : "pause"}
                disabled={room.configured_kill_switch}
              />
            )}
          </section>
          {room?.configured_kill_switch && (
            <p className="analysis-warning">
              Configured kill switch is engaged. Runtime controls cannot
              override it.
            </p>
          )}
          <ChaosPanel data={chaos} />
          <section className="panel telemetry-panel">
            <h2>Measured reliability</h2>
            <div className="war-metrics">
              <div>
                <span>Mean detection delay</span>
                <strong>
                  {metrics?.mean_detection_seconds == null
                    ? "—"
                    : `${metrics.mean_detection_seconds}s`}
                </strong>
                <small>
                  {metrics?.detection_samples ?? "—"} available samples, latest
                  100 incidents
                </small>
              </div>
              <div>
                <span>Mean applied-to-healed time</span>
                <strong>
                  {metrics?.mean_repair_seconds == null
                    ? "—"
                    : `${metrics.mean_repair_seconds}s`}
                </strong>
                <small>
                  {metrics?.repair_samples ?? "—"} verified repairs, latest 100
                </small>
              </div>
              <div>
                <span>Completed diagnoses</span>
                <strong>{metrics?.diagnoses ?? "—"}</strong>
                <small>Validated structured stage outputs</small>
              </div>
              <div>
                <span>Applied repair attempts</span>
                <strong>{metrics?.repair_attempts ?? "—"}</strong>
                <small>
                  {metrics?.failed_repairs ?? "—"} failed or rolled back
                </small>
              </div>
            </div>
          </section>
          <section className="panel event-feed">
            <div className="section-heading">
              <h2>Operations timeline</h2>
              <span>Latest 30 events · routine polls omitted</span>
            </div>
            {room?.events.length ? (
              <ol>
                {room.events.map((e) => (
                  <li key={e.id}>
                    <time>{displayTime(e.created_at)}</time>
                    <div>
                      <strong>{e.kind.replaceAll(".", " · ")}</strong>
                      <p>{e.message}</p>
                      {e.incident_id && (
                        <Link href={`/incidents/${e.incident_id}`}>
                          Incident #{e.incident_id} →
                        </Link>
                      )}
                    </div>
                  </li>
                ))}
              </ol>
            ) : (
              <div className="empty-state">No system events recorded.</div>
            )}
          </section>
          <footer className="war-footer">
            {room
              ? `Snapshot ${displayTime(room.at)}`
              : "No snapshot available"}{" "}
            · Actual records, bounded actions.
          </footer>
        </div>
      </main>
    </div>
  );
}
