"use client";

import { Component, type ErrorInfo, type ReactNode } from "react";
import { ErrorState } from "@/components/ui";
import { Button } from "@/components/ui";

interface ErrorBoundaryProps {
  children: ReactNode;
  /** Optional custom fallback. Receives the error and a reset callback. */
  fallback?: (error: Error, reset: () => void) => ReactNode;
}

interface ErrorBoundaryState {
  error: Error | null;
}

/**
 * Application-level error boundary.
 *
 * Catches render-time exceptions anywhere in the wrapped client subtree so a
 * single broken component degrades gracefully into a recoverable fallback
 * instead of unmounting the whole app. Reusable: wrap any subtree and
 * optionally supply a custom `fallback`.
 */
export class ErrorBoundary extends Component<
  ErrorBoundaryProps,
  ErrorBoundaryState
> {
  state: ErrorBoundaryState = { error: null };

  static getDerivedStateFromError(error: Error): ErrorBoundaryState {
    return { error };
  }

  componentDidCatch(error: Error, info: ErrorInfo) {
    // Surface to the console; a real deployment would forward this to an
    // error-tracking backend (Sentry, etc.).
    console.error("ErrorBoundary caught an error:", error, info.componentStack);
  }

  private reset = () => this.setState({ error: null });

  render() {
    const { error } = this.state;
    if (error) {
      if (this.props.fallback) return this.props.fallback(error, this.reset);
      return (
        <div className="card p-2">
          <ErrorState
            title="Something went wrong"
            message={error.message || "An unexpected error occurred while rendering this view."}
            action={
              <Button variant="secondary" onClick={this.reset}>
                Try again
              </Button>
            }
          />
        </div>
      );
    }
    return this.props.children;
  }
}

export default ErrorBoundary;
