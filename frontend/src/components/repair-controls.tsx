"use client";
import { useState } from "react";
import { useRouter } from "next/navigation";

export function RepairControls({
  id,
  digest,
  mode,
  disabled = false,
}: {
  id?: number;
  digest?: string;
  mode: "prepare" | "decision" | "pause" | "resume" | "reconcile";
  disabled?: boolean;
}) {
  const router = useRouter();
  const [busy, setBusy] = useState(false);
  const [acknowledged, setAcknowledged] = useState(false);
  const [message, setMessage] = useState("");
  async function act(action: string) {
    setBusy(true);
    setMessage("");
    try {
      const response = await fetch("/api/repairs", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ action, id, digest, acknowledged }),
      });
      const data = await response.json();
      if (!response.ok) throw new Error(data.error || "Repair action failed");
      setMessage(
        action === "approve"
          ? "Approval recorded. Follow the persisted execution status below."
          : "Action recorded.",
      );
      router.refresh();
    } catch (error) {
      setMessage(
        error instanceof Error ? error.message : "Repair action failed",
      );
    } finally {
      setBusy(false);
    }
  }
  return (
    <div className="repair-controls">
      {mode === "decision" ? (
        <>
          <label className="maintenance-ack">
            <input
              type="checkbox"
              checked={acknowledged}
              onChange={(e) => setAcknowledged(e.target.checked)}
              disabled={busy || disabled}
            />
            <span>
              I reviewed this diff and authorize its application and conditional
              rollback. This workflow is unpublished and exclusively under
              maintenance. I will avoid concurrent edits and run two full
              executions for verification.
            </span>
          </label>
          <div className="repair-buttons">
            <button
              onClick={() => act("approve")}
              disabled={busy || disabled || !acknowledged}
            >
              Approve repair &amp; rollback
            </button>
            <button
              className="secondary"
              onClick={() => act("reject")}
              disabled={busy}
            >
              Reject
            </button>
          </div>
        </>
      ) : (
        <button
          className={mode === "pause" ? "secondary" : ""}
          onClick={() => act(mode)}
          disabled={busy || disabled}
        >
          {busy
            ? "Saving…"
            : mode === "prepare"
              ? "Prepare repair review"
              : mode === "reconcile"
                ? "Recheck recovery state"
                : mode === "pause"
                  ? "Pause all repair writes"
                  : "Release runtime pause"}
        </button>
      )}
      {message && <p role="status">{message}</p>}
    </div>
  );
}
