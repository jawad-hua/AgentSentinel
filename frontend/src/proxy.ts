import { createHash, timingSafeEqual } from "node:crypto";
import { NextRequest, NextResponse } from "next/server";

const failedAttempts: number[] = [];

function equal(a: string, b: string) {
  return timingSafeEqual(
    createHash("sha256").update(a).digest(),
    createHash("sha256").update(b).digest(),
  );
}

// A single-operator gate, not a multi-user identity or permissions system.
export function proxy(request: NextRequest) {
  let origin: URL;
  try {
    origin = new URL(process.env.CONSOLE_ORIGIN ?? "http://127.0.0.1:3000");
  } catch {
    return new NextResponse("Console origin is invalid", { status: 503 });
  }
  const host = request.headers.get("host");
  const local = ["localhost", "127.0.0.1", "[::1]"].includes(origin.hostname);
  const aliases = new Set([origin.host]);
  if (local) {
    const port = origin.port ? `:${origin.port}` : "";
    aliases.add(`127.0.0.1${port}`);
    aliases.add(`localhost${port}`);
  }
  if (!host || !aliases.has(host))
    return new NextResponse("Host denied", { status: 403 });
  const username = process.env.CONSOLE_USERNAME ?? "";
  const password = process.env.CONSOLE_PASSWORD ?? "";
  if ((!local && origin.protocol !== "https:") ||
      ((!local || username || password) && (!username || password.length < 32)))
    return new NextResponse("Console access is not configured", { status: 503 });
  if (username && password) {
    const expected = `Basic ${Buffer.from(`${username}:${password}`).toString("base64")}`;
    if (!equal(request.headers.get("authorization") ?? "", expected)) {
      const cutoff = Date.now() - 60000;
      while (failedAttempts.length && failedAttempts[0] <= cutoff) failedAttempts.shift();
      if (failedAttempts.length >= 60)
        return new NextResponse("Authentication request budget exceeded", {
          status: 429, headers: { "Retry-After": "60", "Cache-Control": "no-store" },
        });
      failedAttempts.push(Date.now());
      return new NextResponse("Operator authentication required", {
        status: 401,
        headers: {
          "WWW-Authenticate": 'Basic realm="AgentSentinel", charset="UTF-8"',
          "Cache-Control": "no-store",
        },
      });
    }
  }
  const response = NextResponse.next();
  response.headers.set("Cache-Control", "no-store");
  return response;
}

// Cover HTML, RSC, actions, proxies and assets: no alternate unprotected console entry.
export const config = { matcher: "/:path*" };
