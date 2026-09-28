---
name: frontend-ui-engineering
description: Build production-quality React UIs in AS v2 (React 19 + Antd v5 + Tailwind). Use when creating components, implementing pages, managing client state, or modifying any user-facing interface.
---

# Frontend UI Engineering — Aprender Sistema

## Overview

Stack: **React 19 + Ant Design v5 + Tailwind CSS + Vite 7** (migrado do React 18 no #1675;
antd usa o shim `@ant-design/v5-patch-for-react-19`, importado no `main.tsx`). Goal: UI that
matches AS v2's existing design language, not AI-generated-looking output.

Layout under `v2/frontend/src/`: `pages/` (40, lazy-loaded), `components/` (18 reusable),
`hooks/` (14 custom), `api/` (one client per domain).

## The one rule: Antd first

Use Antd components for everything that has one; Tailwind for spacing/layout only.

```tsx
// Good: Antd component, Tailwind for layout
<Card className="mb-4">
  <Space direction="vertical" className="w-full">
    <Typography.Title level={4}>Solicitação</Typography.Title>
  </Space>
</Card>

// Avoid: custom div when Antd has a component
<div className="border rounded p-4 bg-white shadow">  // use <Card>
```

## Reference (read the file for the task at hand)

- Forms, data fetching (`fetchAPI`), polling, state management → `reference/forms.md`
- Tables (`useTableFilters`), empty/loading/error states → `reference/tables.md`
- Accessibility (WCAG), keyboard, ARIA, responsive → `reference/a11y.md`
- Timezone, wizard, approval flow, conflict codes → `reference/domain-patterns.md`

## Anti-Patterns to Avoid

| Anti-Pattern | Why Bad | Correct Approach |
|--------------|---------|------------------|
| `fetch()` direct / raw axios | No CSRF/credentials; axios removed (ADR-013) | `fetchAPI` from `api/config.ts` |
| Custom CSS / inline `style={{padding:15}}` | Off Antd/Tailwind scale | Antd `Space` + Tailwind `p-4`/`gap-*` |
| Manually rendered toasts | Antd has it | `message.error('Erro ao salvar')` |
| Naive date display | UTC ≠ Fortaleza (CP-03) | `.tz('America/Fortaleza')` |
| Redux/Zustand/React Query | Project uses Context + `fetchAPI` + polling | see `reference/forms.md` |
| `React.memo` everywhere | Premature optimization | Only on profiled bottlenecks |
| Vite `manualChunks` | Breaks dep ordering, crashed prod | Never (`feedback_no_manual_chunks.md`) |
| lowercase `fetchpriority` | React 19: `Invalid DOM property` (só o checklist console-errors pega) | camelCase `fetchPriority` |
| `useRef()` sem argumento | React 19 exige valor inicial | `useRef<T>(null)` |
| `import ... from 'react-router-dom'` | v8 removeu o pacote `-dom` (#1675) | `from 'react-router'` |
| Proportional digits in numbers that change or get compared (counters, totals, table columns) | Digits have different widths: values jitter as they update and columns don't line up. Antd v5 doesn't set `tabular-nums` (v4 did) | Tailwind `tabular-nums` on the counter or cell (column `className: 'tabular-nums'`) |
| Pointer target smaller than 40×40px | Missed taps on tablets in the field; antd's default `Button` is 32px, `size="small"` 24px | New or touched controls: `size="large"` (40px) where it fits; in a dense table, enlarge the hit area with a pseudo-element that stops short of the neighbours (`after:absolute after:-inset-1` takes a 32px button to 40px; antd's `Button` is already `position: relative`) |
| Swapping content for a spinner (`if (loading) return <Spin />`) | The page collapses to a spinner and jumps back when data arrives (layout shift) | Keep the component mounted (`<Table loading>`, `<Card loading>`, `<Spin spinning>`) or reserve the final size (`Skeleton` of the same shape) |

## Measure, don't eyeball

A claim about the rendered page ("the target is big enough", "the digits line up", "nothing
jumps when the data arrives") is a number read from the browser, not an impression from a
screenshot. Read it with the Playwright already in `v2/frontend` (`playwright.config.ts`,
specs in `e2e/`; authenticated pages run in the `chromium` project):

```ts
import { test, expect } from '@playwright/test';

test('alvo e dígitos medidos', async ({ page }) => {
  await page.goto('/solicitacoes/minhas');

  // The control you added or touched: visible box >= 40x40px
  const alvo = page.getByRole('button', { name: 'Nova Solicitação' });
  const { width, height } = await alvo.evaluate((el) => el.getBoundingClientRect());
  expect(Math.min(width, height)).toBeGreaterThanOrEqual(40);

  // A numeric column you added: tabular digits are what the browser actually computed
  const numero = page.getByRole('cell').filter({ hasText: /^\d[\d.,]*$/ }).first();
  expect(await numero.evaluate((el) => getComputedStyle(el).fontVariantNumeric))
    .toContain('tabular-nums');
});
```

- **A hit area enlarged by a pseudo-element doesn't show up in `getBoundingClientRect`**,
  which measures the element's own box. Probe a point outside the visible box but inside the
  intended 40px with `document.elementFromPoint(x, y)`; `el.contains(hit)` must be true.
- **Layout shift** is the sum of the `layout-shift` entries without `hadRecentInput`, the same
  sum `getPerformanceMetrics()` does in `e2e/checklist/performance.spec.ts`. Read the entries
  with a buffered `PerformanceObserver`: `performance.getEntriesByType('layout-shift')`, which
  that helper calls, returns no entries in Chromium, so it always reads 0. The callback never
  fires when nothing shifted, hence the timeout:

```ts
const cls = await page.evaluate(() => new Promise<number>((resolve) => {
  type Shift = PerformanceEntry & { value: number; hadRecentInput: boolean };
  new PerformanceObserver((list) => resolve((list.getEntries() as Shift[])
    .reduce((sum, e) => (e.hadRecentInput ? sum : sum + e.value), 0)))
    .observe({ type: 'layout-shift', buffered: true });
  setTimeout(() => resolve(0), 1000);
}));
expect(cls).toBeLessThan(0.1);
```

## Verification Checklist

Before merging a UI change:

- [ ] Antd components used before custom ones
- [ ] Uses `fetchAPI` (not raw fetch or axios)
- [ ] Dates rendered in America/Fortaleza timezone (CP-03)
- [ ] Empty / loading / error states — no blank screens, no layout shift: final size reserved
- [ ] Pointer targets ≥ 40×40px on new or touched controls — measured, not eyeballed
- [ ] Numeric columns and counters use `tabular-nums`
- [ ] Keyboard navigable (Tab through page); icon-only buttons have `aria-label`
- [ ] Responsive at 375 / 768 / 1024 / 1920px
- [ ] No console errors/warnings
- [ ] Lighthouse Performance ≥ 90 for new pages; bundle size not significantly increased
- [ ] E2E checklist passes (`cd v2/frontend && npm run test:checklist`)

## References

- CP-03 (timezone Fortaleza), CP-06 (conventional commits)
- ADR-013: axios pinning → fetch migration (`docs/architecture/project-decisions/`)
- `v2/frontend/src/api/config.ts` — `fetchAPI`, `buildUrl`, `fetchBlob`
- `v2/frontend/src/hooks/useTableFilters.ts`
- Tabular numbers, 40px hit area and no-layout-shift rules adapted from
  [wellwelwel/skills@1c4eb58](https://github.com/wellwelwel/skills/tree/1c4eb580a2a8c9d0257381202a11ffb7380d9d0e/skills/frontend/ui)
  (MIT), itself adapted from
  [jakubkrehel/make-interfaces-feel-better@3845620](https://github.com/jakubkrehel/make-interfaces-feel-better/tree/384562064fcdd99778fcbafd8729626fe6aab02f)
  (MIT) by Jakub Krehel.
