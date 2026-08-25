---
name: frontend-ui-engineering
description: Build production-quality React UIs in AS v2 (React 18 + Antd v5 + Tailwind). Use when creating components, implementing pages, managing client state, or modifying any user-facing interface.
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

## Verification Checklist

Before merging a UI change:

- [ ] Antd components used before custom ones
- [ ] Uses `fetchAPI` (not raw fetch or axios)
- [ ] Dates rendered in America/Fortaleza timezone (CP-03)
- [ ] Empty / loading / error states handled (no blank screens)
- [ ] Keyboard navigable (Tab through page); icon-only buttons have `aria-label`
- [ ] Responsive at 375 / 768 / 1024 / 1920px
- [ ] No console errors/warnings
- [ ] Lighthouse Performance ≥ 90 for new pages; bundle size not significantly increased
- [ ] E2E smoke test passes (`make test-e2e`)

## References

- CP-03 (timezone Fortaleza), CP-06 (conventional commits)
- ADR-013: axios pinning → fetch migration (`docs/architecture/project-decisions/`)
- `v2/frontend/src/api/config.ts` — `fetchAPI`, `buildUrl`, `fetchBlob`
- `v2/frontend/src/hooks/useTableFilters.ts`
