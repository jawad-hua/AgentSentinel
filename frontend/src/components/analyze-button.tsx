"use client";
import { useState } from "react";
import { useRouter } from "next/navigation";

export function AnalyzeButton({
  id,
  disabled,
  again,
  reviewOf,
}: {
  id: number;
  disabled: boolean;
  again: boolean;
  reviewOf?: number;
}) {
  const [pending, setPending] = useState(false);
  const [message, setMessage] = useState("");
  const router = useRouter();
  async function analyze() {
    setPending(true);
    setMessage("");
    try {
      const response = await fetch("/api/investigations", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ incident_id: id, review_of: reviewOf }),
      });
      const result = await response.json();
      if (!response.ok)
        throw new Error(result.error || "Analysis request failed.");
      setMessage(`Investigation #${result.investigation_id} requested.`);
      router.refresh();
    } catch (error) {
      setMessage(
        error instanceof Error ? error.message : "Analysis request failed.",
      );
    } finally {
      setPending(false);
    }
  }
  return (
    <div>
      <button
        className="button"
        disabled={disabled || pending}
        onClick={analyze}
      >
        {pending
          ? "Requesting…"
          : reviewOf
            ? "Request repair assessment"
            : again
              ? "Request another analysis"
              : "Investigate incident"}
      </button>
      <p role="status" aria-live="polite">
        {message}
      </p>
    </div>
  );
}
