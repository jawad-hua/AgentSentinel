import "server-only";
import type { NextRequest } from "next/server";
export function allowedOrigin(request: NextRequest) {
  const origin = process.env.CONSOLE_ORIGIN ?? "http://127.0.0.1:3000";
  return (
    request.headers.get("origin") === origin &&
    request.headers.get("host") === new URL(origin).host
  );
}
