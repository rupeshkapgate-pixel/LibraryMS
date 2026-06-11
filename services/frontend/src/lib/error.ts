export function getErrorMessage(
  error: unknown,
  fallback = "Something went wrong"
): string {
  if (error instanceof Error) {
    return error.message;
  }

  if (
    typeof error === "object" &&
    error !== null &&
    "response" in error
  ) {
    const response = (
      error as {
        response?: {
          data?: {
            detail?: string;
            message?: string;
          };
        };
      }
    ).response;

    return (
      response?.data?.detail ??
      response?.data?.message ??
      fallback
    );
  }

  return fallback;
}