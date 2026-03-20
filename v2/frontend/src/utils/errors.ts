/**
 * Error utilities for consistent error handling across the frontend.
 */

/**
 * Extract HTTP status code from various error shapes (axios, fetch, custom).
 */
export function getErrorStatus(error: unknown): number | undefined {
  if (typeof error === 'object' && error !== null) {
    const err = error as Record<string, unknown>;
    if (typeof err.status === 'number') return err.status;
    if (typeof err.response === 'object' && err.response !== null) {
      const resp = err.response as Record<string, unknown>;
      if (typeof resp.status === 'number') return resp.status;
    }
  }
  return undefined;
}

/**
 * Check if an error is an authentication/authorization error (401 or 403).
 */
export function isAuthError(error: unknown): boolean {
  const status = getErrorStatus(error);
  return status === 401 || status === 403;
}
