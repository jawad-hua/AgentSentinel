import { RepairPanel } from "@/components/repair-panel";
import type { RepairData } from "@/lib/repairs";
import { InvestigationPanel } from "@/components/investigation-panel";
import type { InvestigationData } from "@/lib/investigation";
import Link from "next/link";
import { api } from "@/lib/api";
import type { IncidentDetail } from "@/lib/monitoring";
import { displayTime } from "@/lib/monitoring";
import { LiveUpdates } from "@/components/live-updates";
export const dynamic = "force-dynamic";
export default async function Detail({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;
  const data: IncidentDetail | null = /^\d+$/.test(id)
    ? await api(`/api/v1/incidents/${id}`).catch(() => null)
    : null;
  if (!data)
    return (
      <main className="detail-page">
        <Link href="/incidents">← Incident register</Link>
        <div className="panel empty-state">
          Incident unavailable. Check its ID and service connection.
        </div>
      </main>
    );
  const analysis: InvestigationData | null = await api(
    `/api/v1/incidents/${id}/investigations`,
  ).catch(() => null);
  const repairs: RepairData | null = await api(
    `/api/v1/incidents/${id}/repairs`,
  ).catch(() => null);
  return (
    <main className="detail-page">
      <Link href="/incidents" className="back-link">
        ← Incident register
      </Link>
      <div className="detail-heading">
        <div>
          <span className="eyebrow">INCIDENT #{data.id}</span>
          <h1>{data.kind.replaceAll("_", " ")}</h1>
          <p>{data.workflow_name}</p>
        </div>
        <LiveUpdates />
      </div>
      <section className="panel incident-overview">
        <div>
          <span
            className={`pill ${data.severity === "high" ? "danger" : "warning"}`}
          >
            {data.severity}
          </span>{" "}
          <span className="pill neutral">{data.status}</span>
        </div>
        <h2>{data.summary}</h2>
        <dl className="evidence-grid">
          <div>
            <dt>Affected node</dt>
            <dd>{data.node || "Not identified in available evidence"}</dd>
          </div>
          <div>
            <dt>Occurrences</dt>
            <dd>{data.occurrences}</dd>
          </div>
          <div>
            <dt>First detected</dt>
            <dd>{displayTime(data.detected_at)}</dd>
          </div>
          <div>
            <dt>Last observed</dt>
            <dd>{displayTime(data.last_seen_at)}</dd>
          </div>
          <div>
            <dt>First execution</dt>
            <dd>{data.first_execution_id}</dd>
          </div>
          <div>
            <dt>Latest execution</dt>
            <dd>{data.last_execution_id}</dd>
          </div>
        </dl>
      </section>
      <div className="observed-evidence">
        <section className="panel evidence-panel">
          <span className="eyebrow">OBSERVED EVIDENCE</span>
          <h2>Latest execution facts</h2>
          <dl>
            {Object.entries(data.evidence).map(([key, value]) => (
              <div key={key}>
                <dt>{key.replaceAll("_", " ")}</dt>
                <dd>{String(value)}</dd>
              </div>
            ))}
          </dl>
          <p>
            Raw payloads, credentials and arbitrary error text are excluded.
            Detection categories are deterministic observations, not an AI
            root-cause diagnosis.
          </p>
        </section>
      </div>
      <InvestigationPanel id={data.id} data={analysis} />
      <RepairPanel data={repairs} analysis={analysis} />
      <section className="panel timeline">
        <span className="eyebrow">PERSISTED TIMELINE</span>
        <h2>Incident history</h2>
        <ol>
          {data.timeline.map((event) => (
            <li key={event.id}>
              <time>{displayTime(event.created_at)}</time>
              <strong>{event.kind.replaceAll(".", " · ")}</strong>
              <p>{event.message}</p>
            </li>
          ))}
        </ol>
        <small>Showing up to {data.timeline_limit} most recent events.</small>
      </section>
      <section className="panel evidence-panel">
        <h2>Recent affected executions</h2>
        {data.occurrences_recent.map((item) => (
          <div className="execution-occurrence" key={item.execution_id}>
            <strong>Execution {item.execution_id}</strong>
            <span>{displayTime(item.observed_at)}</span>
          </div>
        ))}
        <small>Latest 20 occurrences. Full occurrence count is retained.</small>
      </section>
    </main>
  );
}
