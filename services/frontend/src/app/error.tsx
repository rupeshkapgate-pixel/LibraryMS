"use client";

import { useEffect } from "react";
import { ErrorState, Button } from "@/components/ui";

/**
 * Route-segment error boundary (Next.js App Router convention).
 * Catches errors thrown while rendering a page and offers a recovery action.
 */
export default function Error({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  useEffect(() => {
    console.error("Route error:", error);
  }, [error]);

  return (
    <div className="card p-2">
      <ErrorState
        title="Something went wrong"
        message={
          error.message ||
          "An unexpected error occurred while loading this page."
        }
        action={<Button onClick={() => reset()}>Try again</Button>}
      />
    </div>
  );
}
