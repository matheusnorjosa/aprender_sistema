# Reference — Forms & Data Fetching

## Data fetching (SSOT)

All HTTP goes through `fetchAPI` from `v2/frontend/src/api/config.ts` (axios removed —
ADR-013). Exports: `fetchAPI<T>`, `buildUrl(path, params)`, `fetchBlob` (CSV/Excel exports),
`fetchWithErrorMapping`. `fetchAPI` adds CSRF + credentials; raw `fetch()`/axios do not.

```tsx
import { fetchAPI, buildUrl } from '../api/config';

export async function listSolicitacoes(params: QueryParams = {}) {
  return fetchAPI<PaginatedResponse<Solicitacao>>(buildUrl('/solicitacoes/', params));
}
```

API clients live in `v2/frontend/src/api/`, one file per domain (e.g. `solicitacoes.ts`).

## Polling

`usePolling` (`v2/frontend/src/hooks/usePolling.ts`) — no React Query.

```tsx
// usePolling(fetchFn, options) — returns void; fetchFn updates state itself.
// options: { enabled (required), intervalMs, events? }
usePolling(getAlertsSummary, {
  enabled: true,
  intervalMs: TIMING.GCAL_POLL_INTERVAL_MS,
});
```

## Antd Form handling

```tsx
import { Form, Input, Button, Select } from 'antd';
import type { Rule } from 'antd/es/form';

const rules: Rule[] = [{ required: true, message: 'Campo obrigatório' }];

<Form layout="vertical" onFinish={handleSubmit}>
  <Form.Item name="municipio" label="Município" rules={rules}>
    <Select
      showSearch
      options={municipios.map(m => ({ value: m.id, label: m.nome }))}
      filterOption={(input, option) =>
        (option?.label ?? '').toLowerCase().includes(input.toLowerCase())
      }
    />
  </Form.Item>
  <Button type="primary" htmlType="submit">Enviar</Button>
</Form>
```

## State management

| Scenario | Approach |
|----------|----------|
| Component UI state | `useState` |
| Theme/auth | Context (`ThemeContext`, `AuthContext`) |
| Filters/pagination | URL searchParams (`useSearchParams`) |
| Server data | `fetchAPI` + local state |
| Shared across pages | context or props (avoid global stores) |

NO Redux/Zustand/TanStack Query — Context API + `fetchAPI` + custom polling hooks (intentional).
