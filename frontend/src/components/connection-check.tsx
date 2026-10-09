"use client";
import { useState } from "react";

export function ConnectionCheck({
  provider,
  configured,
}: {
  provider: "n8n" | "groq";
  configured: boolean;
}) {
  const [state, setState] = useState("Not checked");
  const [busy, setBusy] = useState(false);
  async function check() {
    setBusy(true);
    setState("Checking connection…");
    try {
      const response = await fetch(`/api/connections/${provider}`, {
        method: "POST",
      });
      const body = await response.json();
      setState(
        response.ok
          ? `Connected · checked ${new Date().toLocaleTimeString()}`
          : body.error,
      );
    } catch {
      setState("Connection check unavailable. Try again.");
    } finally {
      setBusy(false);
    }
  }
  return (
    <div className="connection-action">
      <button
        onClick={check}
        disabled={!configured || busy}
        className="button secondary"
      >
        {busy ? "Checking…" : "Check connection"}
      </button>
      <span role="status" className="check-result">
        {configured ? state : "Add credentials to enable checks"}
      </span>
    </div>
  );
}
