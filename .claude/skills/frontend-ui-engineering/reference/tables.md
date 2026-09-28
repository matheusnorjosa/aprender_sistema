# Reference — Tables

Use `useTableFilters` (`v2/frontend/src/hooks/useTableFilters.ts`) for consistent
filter/pagination behavior.

```tsx
import { useTableFilters } from '../hooks/useTableFilters';

// 3 type params <Filters, Row, Stats>; defaultFilters + listFn are required.
const {
  data, loading, filters, setFilters,
  pagination, handleTableChange, handleClearFilters,
} = useTableFilters<MyFilters, MyRow, MyStats>({
  defaultFilters: { status: 'pendente' },
  listFn: listSolicitacoes,
  buildParams: (f) => ({ ...(f.status && { status: f.status }) }),
});

<Table
  dataSource={data}
  columns={columns}
  loading={loading}
  pagination={pagination}
  onChange={handleTableChange}
/>
```

Filter param names must match the backend FilterSet field exactly — a name the FilterSet
doesn't declare is silently ignored (no error, empty filter). Check the relevant FilterSet
(e.g. `v2/backend/apps/core/views/dat_module.py`) for whether an FK filter is `municipio`
or `municipio_id` before wiring the query param.

## Empty / loading / error states

Always handle all three — never a blank screen. Keep the `Table` mounted while it loads:
`loading` overlays the current rows, so the page doesn't collapse to a spinner and jump back
(layout shift). The empty state goes in `locale.emptyText`, not in an early return, which
would also replace the table during the first load:

```tsx
if (error) return <Alert type="error" message={error} showIcon />;
return (
  <Table
    dataSource={data}
    columns={columns}
    loading={loading}
    locale={{ emptyText: <Empty description="Nenhuma solicitação encontrada" /> }}
  />
);
```
