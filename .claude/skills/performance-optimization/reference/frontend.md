# Frontend Performance Reference (React 18 / Vite / Antd)

Anti-pattern catalogue and profiling recipes. Inline workflow lives in `SKILL.md`.

## Lighthouse (CI)

```bash
cd v2/frontend && npm run lighthouse:ci   # → node scripts/lighthouse-ci.mjs
```

Thresholds from `v2/frontend/lighthouserc.cjs` (desktop preset, 3 runs):

| Category | Threshold | Severity |
|----------|-----------|----------|
| Performance | ≥ 70 | error (fails CI) |
| Accessibility | ≥ 90 | error (fails CI) |
| Best Practices | ≥ 90 | warn |
| SEO | ≥ 90 | warn |
| LCP | ≤ 2500ms | error |
| CLS | ≤ 0.1 | error |
| Total Blocking Time | ≤ 300ms | error |

## Bundle Analysis

```bash
docker exec aprender_dev-web-1 bash -c "cd /app/frontend && npm run build -- --mode production && du -sh dist/assets/*.js | sort -h"

# Or visualise
cd v2/frontend && npm run build && npx vite-bundle-visualizer
```

## Anti-Patterns

### Unnecessary Re-renders

```tsx
// BAD: New object every render → children re-render
function SolicitacoesList() {
  return <FilterBar options={{ sortBy: 'date' }} />;  // new object each time
}

// GOOD: Stable reference
const DEFAULT_OPTIONS = { sortBy: 'date' } as const;
function SolicitacoesList() {
  return <FilterBar options={DEFAULT_OPTIONS} />;
}
```

Don't scatter `React.memo` without profiling — over-memoization adds its own cost.

### Large Antd / Icon Imports

```tsx
// GOOD: specific icon (tree-shakeable)
import { PlusOutlined } from '@ant-design/icons';

// BAD: pulls in every icon
import * as Icons from '@ant-design/icons';
```

Antd ES modules tree-shake under Vite; the risk is wildcard icon imports.

### Missing Code Splitting

Routes are lazy-loaded in `v2/frontend/src/components/AppRoutes.tsx`:

```tsx
const MySolicitacoesPage = lazy(() => import('../pages/Solicitacoes/MySolicitacoesPage'));

<Suspense fallback={<Spin />}>
  <Routes>
    <Route path="/solicitacoes/minhas" element={<MySolicitacoesPage />} />
  </Routes>
</Suspense>
```

### Vite manualChunks — NEVER USE

```ts
// NEVER — breaks Rollup dep ordering, caused a prod crash
// Memory: feedback_no_manual_chunks.md
build: { rollupOptions: { output: { manualChunks: { /* ... */ } } } }
```

### Image Optimization

```tsx
// GOOD: dimensions + lazy + decoding
<img src="/logo.png" width={200} height={40} loading="lazy" decoding="async" alt="Logo" />

// LCP images (hero, above the fold): fetchpriority LOWERCASE (React 18 warns on camelCase)
<img src="/hero.webp" width={1200} height={600} fetchpriority="high" alt="..." />
```

## Frontend Caching

- CSRF token cached in memory (`src/api/config.ts`), TTL `TIMING.CSRF_TOKEN_TTL_MS`
  = 30 min (`src/constants/timing.ts`).
- Polling hooks use `deduplicatedFetch` (`src/utils/request.ts`) to collapse
  concurrent identical calls.
