import type { NextConfig } from "next";
const config: NextConfig = {
  poweredByHeader: false,
  // Next 16.3.8's compressed Node stream can retain drain listeners under backpressure.
  // Loopback deployment: avoid that path without hiding EventEmitter warnings.
  compress: false,
  experimental: { cpus: 1 },
  async headers() {
    return [
      {
        source: "/:path*",
        headers: [
          { key: "X-Content-Type-Options", value: "nosniff" },
          { key: "X-Frame-Options", value: "DENY" },
          { key: "Referrer-Policy", value: "no-referrer" },
        ],
      },
    ];
  },
};
export default config;
