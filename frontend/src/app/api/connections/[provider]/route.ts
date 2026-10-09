import { NextRequest, NextResponse } from "next/server";
import { api } from "@/lib/api";

export async function POST(
  request: NextRequest,
  context: { params: Promise<{ provider: string }> },
) {
  // Local console only; prevent cross-origin sites from driving authenticated probes.
  const origin = request.headers.get("origin");
  const allowedOrigin = process.env.CONSOLE_ORIGIN ?? "http://127.0.0.1:3000";
  if (
    origin !== allowedOrigin ||
    request.headers.get("host") !== new URL(allowedOrigin).host
  ) {
    return NextResponse.json({ error: "Origin denied" }, { status: 403 });
  }
  const { provider } = await context.params;
  if (!["n8n", "groq"].includes(provider)) {
    return NextResponse.json({ error: "Unknown integration" }, { status: 404 });
  }
  try {
    return NextResponse.json(
      await api(`/api/v1/integrations/${provider}/check`, "POST"),
    );
  } catch {
    return NextResponse.json(
      {
        error:
          "Connection check failed. Check the API key, service URL and model configuration.",
      },
      { status: 502 },
    );
  }
}
