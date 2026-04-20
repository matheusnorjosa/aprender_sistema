# Frontend Test Strategy: MSW vs `vi.mock`

Adopted in issue [#849](https://github.com/matheusnorjosa/aprender_sistema/issues/849) (part of epic [#845](https://github.com/matheusnorjosa/aprender_sistema/issues/845)).

## TL;DR — which to reach for

| Use MSW when… | Use `vi.mock` / `vi.fn()` when… |
|---|---|
| You test a **component/hook/page** that calls `fetchAPI`. | You test a pure helper that does not hit the network. |
| You test an **API client module** (`src/api/*.ts`) end-to-end. | You test a hook that accepts a function callback as prop (pass `vi.fn()`). |
| You want to assert on **response handling** (error paths, pagination shapes). | You want to assert on **wrapper invocation** (how many times, with what URL). |
| The test crosses multiple API calls and cares about ordering. | The test exercises a single seam with a simple double. |

Default to MSW for any new test that touches the API boundary. Fall back to
`vi.mock` for unit tests where the HTTP layer is not interesting.

## Infrastructure

- **Handlers**: `v2/frontend/src/test/mocks/handlers.ts` — default handlers
  (e.g. `/api/csrf/`). Keep this minimal. Scenario-specific handlers live in
  tests via `server.use(...)`.
- **Server**: `v2/frontend/src/test/mocks/server.ts` — `setupServer` instance.
- **Lifecycle**: wired in `v2/frontend/src/test/setup.js`.
  - `beforeAll`: `server.listen({ onUnhandledRequest: 'bypass' })`
  - `afterEach`: `server.resetHandlers()`
  - `afterAll`: `server.close()`

### Why `onUnhandledRequest: 'bypass'` (for now)

During rollout many existing tests still use `vi.mock('../config')` to
replace `fetchAPI`. Those never hit the MSW layer, so `'error'` would be
noisy. Once a majority of tests have migrated, flip this to `'error'` so
that forgetting a handler fails loudly.

### `apiUrl(path)` helper

`src/test/mocks/handlers.ts` exports `apiUrl('/me/') === '/api/me/'`. Always
use it when registering handlers — it keeps the base URL in one place.

## Pattern — migrating an API client test

### Before (`vi.mock`, asserts on `fetchAPI` calls)

```ts
const { fetchAPIMock } = vi.hoisted(() => ({ fetchAPIMock: vi.fn() }));
vi.mock('../config', () => ({ fetchAPI: fetchAPIMock, buildUrl: (p: string) => p }));
import { getMe } from '../availability';

test('getMe returns data', async () => {
  fetchAPIMock.mockResolvedValue({ id: 1, /* ... */ });
  const user = await getMe();
  expect(fetchAPIMock).toHaveBeenCalledWith('/me/');
  expect(user).toEqual(/* ... */);
});
```

### After (MSW, asserts on behavior)

```ts
import { http, HttpResponse } from 'msw';
import { server } from '../../test/mocks/server';
import { apiUrl } from '../../test/mocks/handlers';
import { getMe } from '../availability';

test('getMe returns data', async () => {
  server.use(
    http.get(apiUrl('/me/'), () => HttpResponse.json({ id: 1, /* ... */ })),
  );
  const user = await getMe();
  expect(user).toEqual(/* ... */);
});
```

The assertion shifts from "was `fetchAPI` called with this URL" to "given
this HTTP response, does the client return the right shape". The URL check
is implicit — if nobody matched the handler, MSW would return a 404 (with
`onUnhandledRequest: 'error'`, it would throw).

## Pattern — migrating a component/page test

When a component test currently does `vi.mock('../../../api/solicitacoes')`,
prefer MSW so the real API client runs and exercises validation, header
handling, and error mapping. Example sketch:

```ts
server.use(
  http.post(apiUrl('/solicitacoes/'), async ({ request }) => {
    const body = await request.json();
    // optional: assert on body shape here
    return HttpResponse.json({ id: 42, ...body }, { status: 201 });
  }),
);

render(<NewSolicitacaoWizard />);
await userEvent.click(screen.getByRole('button', { name: /criar/i }));
expect(await screen.findByText(/#42/)).toBeInTheDocument();
```

Mock React Router, Antd modals, and other *browser* concerns with
`vi.mock` as before — those are not HTTP concerns.

## Pattern — staying with `vi.fn()` for dependency-injected callbacks

Hooks like `useTableFilters({ listFn, statsFn })` accept functions as
props. Those are not HTTP — they are plain JS contracts. Keep using
`vi.fn()` + `mockResolvedValue(...)` there; MSW offers no advantage.

## CSRF & credentials

- The default handler for `GET /api/csrf/` returns `{ csrfToken: 'msw-test-csrf-token' }`.
- `fetchAPI` includes `credentials: 'include'`; MSW honors this.
- If a mutation test cares about the CSRF header, assert on the request
  headers inside the handler:

  ```ts
  server.use(
    http.post(apiUrl('/x/'), ({ request }) => {
      const token = request.headers.get('x-csrftoken');
      expect(token).toBeTruthy();
      return HttpResponse.json({}, { status: 200 });
    }),
  );
  ```

## Roadmap

1. ✅ **Phase 1** — Infrastructure + one pilot migration (`availability.test.ts`).
2. **Phase 2** — Migrate the Tier-1 API client tests (`adminDAT`, `datModule`,
   `gcal`, `lookup`, `systemConfig`). Each can be its own PR.
3. **Phase 3** — Migrate component/page tests that mock API modules
   (`NewSolicitacaoWizard`, etc.). These produce the biggest fidelity gain.
4. **Phase 4** — Flip `onUnhandledRequest` from `'bypass'` to `'error'` once
   the long tail is covered, and remove the remaining `vi.mock('../config')`
   callsites.

## Related

- Epic: [#845 — Testing Maturity](https://github.com/matheusnorjosa/aprender_sistema/issues/845)
- Issue: [#849 — Adopt MSW for frontend integration tests](https://github.com/matheusnorjosa/aprender_sistema/issues/849)
- Coverage policy: [`v2/docs/analysis/COVERAGE_POLICY.md`](analysis/COVERAGE_POLICY.md)
