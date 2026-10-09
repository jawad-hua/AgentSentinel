import { boundedText } from "@/lib/request-body";
import { NextRequest, NextResponse } from "next/server";
import { api } from "@/lib/api";
import { allowedOrigin } from "@/lib/origin";

export async function POST(request: NextRequest) {
  if (!allowedOrigin(request))
    return NextResponse.json({ error: "Origin denied" }, { status: 403 });
  try {
    const text = await boundedText(request, 1024);
    if (text.length > 1024)
      return NextResponse.json({ error: "Request too large" }, { status: 413 });
    const body = JSON.parse(text);
    if (!Number.isSafeInteger(body.incident_id) || body.incident_id < 1)
      return NextResponse.json({ error: "Invalid incident" }, { status: 400 });
    if (
      body.review_of !== undefined &&
      (!Number.isSafeInteger(body.review_of) || body.review_of < 1)
    )
      return NextResponse.json(
        { error: "Invalid source investigation" },
        { status: 400 },
      );
    const path =
      `/api/v1/incidents/${body.incident_id}/investigations` +
      (body.review_of === undefined ? "" : `/${body.review_of}/assessment`);
    return NextResponse.json(await api(path, "POST"), { status: 202 });
  } catch (error) {
    return NextResponse.json(
      {
        error:
          error instanceof Error ? error.message : "Analysis request failed",
      },
      { status: 502 },
    );
  }
}
