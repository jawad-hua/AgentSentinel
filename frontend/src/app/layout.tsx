import type { Metadata } from "next";
import "./globals.css";
export const metadata: Metadata = {
  title: "AgentSentinel · Reliability Console",
  description: "Evidence-driven reliability for AI automations.",
  robots: { index: false, follow: false },
};
export default function RootLayout({
  children,
}: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
