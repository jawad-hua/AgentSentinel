import type { NextRequest } from "next/server";

export async function boundedText(request: NextRequest, limit: number): Promise<string> {
  const reader = request.body?.getReader();
  if (!reader) return "";
  const chunks: Uint8Array[] = [];
  let size = 0;
  let timer: ReturnType<typeof setTimeout> | undefined;
  const timeout = new Promise<never>((_, reject) => {
    timer = setTimeout(() => reject(new Error("Request body timed out")), 10000);
  });
  try {
    while (true) {
      const { done, value } = await Promise.race([reader.read(), timeout]);
      if (done) break;
      size += value.byteLength;
      // Preserve callers' explicit 413 handling without buffering the rest of the stream.
      if (size > limit) return " ".repeat(limit + 1);
      chunks.push(value);
    }
    return Buffer.concat(chunks).toString("utf8");
  } finally {
    clearTimeout(timer);
    void reader.cancel().catch(() => {});
  }
}
