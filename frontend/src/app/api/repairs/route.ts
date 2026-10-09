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
    let path: string;
    let payload: unknown;
    if (body.action === "pause" || body.action === "resume") {
      path = "/api/v1/repair-safety";
      payload = { paused: body.action === "pause" };
    } else if (
      body.action === "reconcile" &&
      Number.isSafeInteger(body.id) &&
      body.id > 0
    ) {
      path = `/api/v1/repairs/${body.id}/reconcile`;
      payload = undefined;
    } else if (
      body.action === "prepare" &&
      Number.isSafeInteger(body.id) &&
      body.id > 0
    ) {
      path = "/api/v1/repairs";
      payload = { investigation_id: body.id };
    } else if (
      ["approve", "reject"].includes(body.action) &&
      Number.isSafeInteger(body.id) &&
      body.id > 0 &&
      typeof body.digest === "string" &&
      /^[a-f0-9]{64}$/.test(body.digest) &&
      typeof body.acknowledged === "boolean"
    ) {
      path = `/api/v1/repairs/${body.id}/decision`;
      payload = {
        action: body.action,
        digest: body.digest,
        maintenance_acknowledged: body.acknowledged,
      };
    } else
      return NextResponse.json(
        { error: "Invalid repair action" },
        { status: 400 },
      );
    return NextResponse.json(await api(path, "POST", payload));
  } catch (error) {
    return NextResponse.json(
      {
        error: error instanceof Error ? error.message : "Repair action failed",
      },
      { status: 502 },
    );
  }
}
