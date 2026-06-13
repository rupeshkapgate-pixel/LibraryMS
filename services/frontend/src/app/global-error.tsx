"use client";

import { useEffect } from "react";

/**
 * Application-level (root) error boundary.
 *
 * Catches errors thrown in the root layout itself. It fully replaces the app
 * shell, so it must render its own <html>/<body> and cannot depend on layout
 * styling — hence the inline styles below.
 */
export default function GlobalError({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  useEffect(() => {
    console.error("Global error:", error);
  }, [error]);

  return (
    <html lang="en">
      <body
        style={{
          margin: 0,
          minHeight: "100vh",
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          fontFamily:
            "ui-sans-serif, system-ui, -apple-system, Segoe UI, Roboto, sans-serif",
          background: "#f8fafc",
          color: "#0f172a",
        }}
      >
        <div
          style={{
            maxWidth: 420,
            textAlign: "center",
            padding: "2rem",
            borderRadius: 16,
            background: "#ffffff",
            boxShadow: "0 10px 30px rgba(2,6,23,0.08)",
          }}
        >
          <h1 style={{ fontSize: "1.125rem", fontWeight: 600, margin: "0 0 0.5rem" }}>
            Application error
          </h1>
          <p style={{ fontSize: "0.875rem", color: "#64748b", margin: "0 0 1.25rem" }}>
            {error.message || "A critical error occurred. Please try again."}
          </p>
          <button
            type="button"
            onClick={() => reset()}
            style={{
              padding: "0.6rem 1.1rem",
              borderRadius: 10,
              border: "none",
              background: "#4f46e5",
              color: "#fff",
              fontWeight: 600,
              fontSize: "0.875rem",
              cursor: "pointer",
            }}
          >
            Try again
          </button>
        </div>
      </body>
    </html>
  );
}
