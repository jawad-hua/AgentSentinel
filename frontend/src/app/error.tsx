"use client";
export default function ErrorPage({ reset }: { reset: () => void }) {
  return (
    <main className="loading">
      <h1>Console unavailable</h1>
      <p>We could not load the console.</p>
      <button className="button" onClick={reset}>
        Try again
      </button>
    </main>
  );
}
