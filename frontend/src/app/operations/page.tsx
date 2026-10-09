import Link from "next/link";
import { api } from "@/lib/api";
import type { Catalog, IncidentList } from "@/lib/monitoring";
import { MonitoringPanel } from "@/components/monitoring-panel";
import { systemStatus, type SystemStatus } from "@/lib/api";
import { ConnectionCheck } from "@/components/connection-check";
import { Refresh } from "@/components/refresh";
export const dynamic = "force-dynamic";

export default async function Home() {
  let status: SystemStatus | null = null;
  try {
    status = await systemStatus();
  } catch {
    /* Render a truthful unavailable state. */
  }
  const [catalog, incidents] = await Promise.all([
    api("/api/v1/workflows").catch(() => null) as Promise<Catalog | null>,
    api("/api/v1/incidents?limit=5").catch(
      () => null,
    ) as Promise<IncidentList | null>,
  ]);
  return (
    <div className="app-shell">
      <aside className="sidebar">
        <Link href="/" className="brand">
          <span className="brand-icon">S</span>AgentSentinel
        </Link>
        <div className="workspace">
          <span className="eyebrow">WORKSPACE</span>
          <strong>Local operations</strong>
          <small>Private operator console</small>
        </div>
        <nav aria-label="Main navigation">
          <a className="nav-active" href="#overview">
            ◈ <span>Overview</span>
          </a>
          <a href="#monitoring">
            ◉ <span>Execution watch</span>
          </a>
          <a href="#incidents">
            ◇ <span>Incidents</span>
          </a>
          <a href="#connections">
            ⇄ <span>Connections</span>
          </a>
          <a href="#safety">
            ⊙ <span>Safety controls</span>
          </a>
        </nav>
        <div className="sidebar-bottom">
          <span className="tiny-dot" />
          Evidence before action<small>Reliability, under your control.</small>
        </div>
      </aside>
      <main id="overview">
        <header className="topbar">
          <span>
            Operations <span className="muted">/ Overview</span>
          </span>
          <span className="local-tag">LOCAL ENVIRONMENT</span>
        </header>
        <div className="content">
          <div className="page-heading">
            <div>
              <span className="eyebrow">RELIABILITY CONSOLE</span>
              <h1>
                Your automation,
                <br />
                under watch.
              </h1>
              <p>A clear view of your connections and operational readiness.</p>
            </div>
            <Refresh />
          </div>
          {!status && (
            <div role="alert" className="error-banner">
              <strong>Service unavailable</strong>
              <p>
                Start the API, apply database migrations and check your local
                configuration. No operational state could be loaded.
              </p>
            </div>
          )}
          <section className="readiness panel" aria-label="Service readiness">
            <div className="status-symbol">{status ? "◎" : "!"}</div>
            <div>
              <span className="eyebrow">SERVICE READINESS</span>
              <h2>{status ? "Service online" : "Connection required"}</h2>
              <p>
                {status
                  ? status.monitoring_enabled
                    ? "The service is watching your selected workflows. See each workflow for evidence and freshness."
                    : "Service and database are reachable. Enable monitoring for selected workflows below."
                  : "Connect the service to inspect its actual state."}
              </p>
            </div>
            <span className={`pill ${status ? "success" : "warning"}`}>
              {status ? "SERVICE READY" : "UNAVAILABLE"}
            </span>
          </section>
          <section className="metrics" aria-label="System state">
            <article className="panel metric">
              <span>Database</span>
              <strong>{status ? "Connected" : "Unavailable"}</strong>
              <small>Checked by the service request</small>
            </article>
            <article className="panel metric">
              <span>Received heartbeats</span>
              <strong>{status?.heartbeat_count ?? "—"}</strong>
              <small>Unique executions recorded in the database</small>
            </article>
            <article className="panel metric">
              <span>Last heartbeat</span>
              <strong className="date-value">
                {status?.last_heartbeat
                  ? new Date(status.last_heartbeat)
                      .toISOString()
                      .replace("T", " ")
                      .slice(0, 19) + " UTC"
                  : status
                    ? "Not received"
                    : "Unavailable"}
              </strong>
              <small>A heartbeat confirms delivery, not workflow health</small>
            </article>
          </section>
          <section className="metrics" aria-label="Monitoring totals">
            <article className="panel metric">
              <span>Enabled workflows</span>
              <strong>{status?.monitored_workflows ?? "—"}</strong>
              <small>Explicit operator selections</small>
            </article>
            <article className="panel metric">
              <span>Observed executions</span>
              <strong>{status?.execution_count ?? "—"}</strong>
              <small>Recorded from the n8n API</small>
            </article>
            <article className="panel metric">
              <span>Recorded incidents</span>
              <strong>{status?.incident_count ?? "—"}</strong>
              <small>Distinct observed failure signatures</small>
            </article>
          </section>
          <MonitoringPanel catalog={catalog} incidents={incidents} />
          <section id="connections">
            <div className="section-heading">
              <h2>Connected services</h2>
              <span>Credentials remain on the server</span>
            </div>
            <div className="connections">
              {(["n8n", "groq"] as const).map((provider) => (
                <article key={provider} className="panel connection">
                  <div className="connection-title">
                    <div className={`provider-icon ${provider}`}>
                      {provider === "n8n" ? "n8n" : "g"}
                    </div>
                    <div>
                      <h3>
                        {provider === "n8n"
                          ? "n8n Automation"
                          : "Groq Inference"}
                      </h3>
                      <p>
                        {provider === "n8n"
                          ? "Workflow and execution API"
                          : "External structured reasoning"}
                      </p>
                    </div>
                  </div>
                  <span className="pill neutral">
                    {status
                      ? status.integrations[provider]
                        ? "CONFIGURED · UNVERIFIED"
                        : "NOT CONFIGURED"
                      : "STATUS UNAVAILABLE"}
                  </span>
                  <ConnectionCheck
                    provider={provider}
                    configured={!!status?.integrations[provider]}
                  />
                </article>
              ))}
            </div>
          </section>
          <section className="bottom-grid">
            <article className="panel activity">
              <span className="eyebrow">AUTOMATION RELIABILITY</span>
              <div className="empty-icon">⌁</div>
              <h2>Evidence before diagnosis</h2>
              <p>
                Detection is driven by actual execution traces. Incidents and
                agent activity will appear only after real evidence is
                collected.
              </p>
              <span className="text-label">
                No synthetic activity. No assumed health.
              </span>
            </article>
            <article id="safety" className="panel safety">
              <span className="eyebrow">SAFETY POSTURE</span>
              <h2>Controlled by design.</h2>
              <div className="safety-row">
                <span>Kill switch</span>
                <strong>
                  {status
                    ? status.kill_switch
                      ? "Engaged"
                      : "Disengaged"
                    : "Unknown"}
                </strong>
              </div>
              <div className="safety-row">
                <span>Workflow modifications</span>
                <strong>{status ? "Unavailable" : "Unknown"}</strong>
              </div>
              <div className="safety-row">
                <span>Autonomous repairs</span>
                <strong>{status ? "Not enabled" : "Unknown"}</strong>
              </div>
              <p>
                No workflow mutation endpoints exist in this release. Restart
                the service after changing local safety configuration.
              </p>
            </article>
          </section>
          <footer>
            <span>AgentSentinel{status ? ` / v${status.version}` : ""}</span>
            <span>Real evidence. Deliberate action.</span>
          </footer>
        </div>
      </main>
    </div>
  );
}
