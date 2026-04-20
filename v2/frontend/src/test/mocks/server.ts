/**
 * MSW server for Vitest (Node/jsdom environment).
 *
 * Lifecycle is wired from src/test/setup.js:
 *   - beforeAll  → server.listen({ onUnhandledRequest: 'error' })
 *   - afterEach  → server.resetHandlers()
 *   - afterAll   → server.close()
 *
 * Tests add scenario-specific handlers via `server.use(...)`:
 *
 *   import { server } from '@/test/mocks/server';
 *   import { http, HttpResponse } from 'msw';
 *
 *   server.use(
 *     http.get('/api/me/', () => HttpResponse.json({ id: 1, ... })),
 *   );
 */
import { setupServer } from 'msw/node';
import { handlers } from './handlers';

export const server = setupServer(...handlers);
