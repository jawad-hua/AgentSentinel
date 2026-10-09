import { NextRequest } from "next/server";
export const dynamic = "force-dynamic";
export async function GET(request: NextRequest) {
  const base = process.env.AGENTSENTINEL_API_URL;
  const token = process.env.ADMIN_API_TOKEN;
  if (!base || !token)
    return new Response("Service not configured", { status: 503 });
  try {
    const headers: Record<string, string> = {
      Authorization: `Bearer ${token}`,
    };
    const cursor = request.headers.get("last-event-id");
    if (cursor) headers["Last-Event-ID"] = cursor;
    const response = await fetch(`${base}/api/v1/events`, {
      headers,
      signal: request.signal,
      cache: "no-store",
      redirect: "error",
    });
    if (!response.ok)
      return new Response("Event stream unavailable", { status: 502 });
    return new Response(response.body, {
      headers: {
        "Content-Type": "text/event-stream",
        "Cache-Control": "no-cache, no-transform",
        "X-Accel-Buffering": "no",
      },
    });
  } catch {
    return new Response("Event stream unavailable", { status: 503 });
  }
}
