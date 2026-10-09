"use client";
import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
export function LiveUpdates() {
  const router = useRouter();
  const [connected, setConnected] = useState(false);
  useEffect(() => {
    const stream = new EventSource("/api/events");
    let timer: ReturnType<typeof setTimeout> | undefined;
    const refresh = () => {
      if (!timer)
        timer = setTimeout(() => {
          router.refresh();
          timer = undefined;
        }, 500);
    };
    stream.addEventListener("ready", () => {
      setConnected(true);
      refresh();
    });
    stream.onmessage = refresh;
    stream.onerror = () => setConnected(false);
    // Refresh freshness labels even when no events arrive, without fabricating activity.
    const freshness = setInterval(refresh, 30000);
    return () => {
      stream.close();
      clearInterval(freshness);
      if (timer) clearTimeout(timer);
    };
  }, [router]);
  return (
    <span className={`pill ${connected ? "success" : "neutral"}`} role="status">
      {connected ? "LIVE UPDATES CONNECTED" : "LIVE UPDATES RECONNECTING"}
    </span>
  );
}
