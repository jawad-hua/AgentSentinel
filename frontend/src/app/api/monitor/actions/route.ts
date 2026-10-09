import { boundedText } from "@/lib/request-body";
import { NextRequest, NextResponse } from "next/server";
import { api } from "@/lib/api";
import { allowedOrigin } from "@/lib/origin";
export async function POST(request: NextRequest) {
  if (!allowedOrigin(request))
    return NextResponse.json({ error: "Origin denied" }, { status: 403 });
  try {
    const text = await boundedText(request, 8192);
    if (text.length > 8192)
      return NextResponse.json({ error: "Request too large" }, { status: 413 });
    const body = JSON.parse(text);
    if (body.action === "sync")
      return NextResponse.json(await api("/api/v1/workflows/sync", "POST"));
    if (body.action === "poll")
      return NextResponse.json(await api("/api/v1/monitor/poll", "POST"));
    if (
      body.action === "configure" &&
      typeof body.id === "string" &&
      /^[A-Za-z0-9_-]{1,128}$/.test(body.id)
    ) {
      return NextResponse.json(
        await api(`/api/v1/workflows/${body.id}`, "PATCH", body.config),
      );
    }
    return NextResponse.json({ error: "Invalid action" }, { status: 400 });
  } catch (error) {
    return NextResponse.json(
      { error: error instanceof Error ? error.message : "Action failed" },
      { status: 502 },
    );
  }
}
