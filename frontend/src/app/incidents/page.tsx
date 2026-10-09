import Link from "next/link";
import { api } from "@/lib/api";
import type { IncidentList } from "@/lib/monitoring";
import { displayTime } from "@/lib/monitoring";
import { LiveUpdates } from "@/components/live-updates";
export const dynamic = "force-dynamic";
export default async function Incidents({
  searchParams,
}: {
  searchParams: Promise<{ before?: string }>;
}) {
  const { before } = await searchParams;
  const suffix = before && /^\d+$/.test(before) ? `?before=${before}` : "";
  const data: IncidentList | null = await api(
    `/api/v1/incidents${suffix}`,
  ).catch(() => null);
  return (
    <main className="detail-page">
      <Link href="/" className="back-link">
        ← Operations overview
      </Link>
      <div className="detail-heading">
        <div>
          <span className="eyebrow">PERSISTED OBSERVATIONS</span>
          <h1>Incident register</h1>
        </div>
        <LiveUpdates />
      </div>
      {!data ? (
        <div className="panel empty-state">
          Incident service unavailable. No state could be loaded.
        </div>
      ) : data.items.length === 0 ? (
        <div className="panel empty-state">
          No incidents recorded on this page.
        </div>
      ) : (
        <div className="panel incident-list">
          {data.items.map((row) => (
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
                <strong>
                  #{row.id} · {row.summary}
                </strong>
                <small>
                  {row.workflow_name} · {displayTime(row.detected_at)}
                </small>
              </div>
              <span>{row.occurrences} observed</span>
            </Link>
          ))}
        </div>
      )}
      {data?.next_before && (
        <Link
          className="back-link"
          href={`/incidents?before=${data.next_before}`}
        >
          Older incidents →
        </Link>
      )}
    </main>
  );
}
