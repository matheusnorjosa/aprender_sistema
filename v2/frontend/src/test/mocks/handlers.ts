/**
 * MSW default handlers.
 *
 * These cover endpoints that most integration tests need available by default
 * (CSRF, current user). Individual tests override or add handlers via
 * `server.use(...)` for behavior specific to their scenario.
 *
 * See v2/docs/TESTING_MSW.md for usage guidance.
 */
import { http, HttpResponse } from 'msw';

/**
 * Base URL used by the API client. Must match `API_BASE` resolved at runtime
 * (see src/api/config.ts). Tests run in jsdom without Vite env, so VITE_API_URL
 * is unset and `/api` is used.
 */
export const API_BASE = '/api';

/**
 * Convenience to prefix a backend path with the API base.
 *   apiUrl('/me/') === '/api/me/'
 */
export const apiUrl = (path: string): string =>
  `${API_BASE}${path.startsWith('/') ? path : `/${path}`}`;

/**
 * Default request handlers. Keep this list minimal and broadly useful. If a
 * scenario needs specific payloads, override inline with `server.use(...)`.
 */
export const handlers = [
  // CSRF token issuance — many mutation paths call this first.
  http.get(apiUrl('/csrf/'), () =>
    HttpResponse.json({ csrfToken: 'msw-test-csrf-token' }),
  ),
];
