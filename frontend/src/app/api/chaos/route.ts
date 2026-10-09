import { boundedText } from "@/lib/request-body";
import { NextRequest, NextResponse } from "next/server";
import { api } from "@/lib/api";
import { allowedOrigin } from "@/lib/origin";
export async function POST(request: NextRequest) {
  if (!allowedOrigin(request))
    return NextResponse.json({ error: "Origin denied" }, { status: 403 });
  try {
    const text = await boundedText(request, 2048);
    if (text.length > 2048)
      return NextResponse.json({ error: "Request too large" }, { status: 413 });
    const body = JSON.parse(text);
    if (
      !["designate", "transient", "persistent", "stop"].includes(body.action) ||
      typeof body.workflow_id !== "string" ||
      !/^[A-Za-z0-9_-]{1,128}$/.test(body.workflow_id) ||
      typeof body.acknowledged !== "boolean" ||
      typeof body.baseline_execution !== "string" ||
      !/^[A-Za-z0-9_-]{0,128}$/.test(body.baseline_execution)
    )
      return NextResponse.json(
        { error: "Invalid chaos action" },
        { status: 400 },
      );
    return NextResponse.json(await api("/api/v1/chaos", "POST", body));
  } catch (e) {
    return NextResponse.json(
      { error: e instanceof Error ? e.message : "Chaos request failed" },
      { status: 502 },
    );
  }
}
