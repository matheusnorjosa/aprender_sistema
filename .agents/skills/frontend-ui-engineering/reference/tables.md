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

Always handle all three — never a blank screen:

```tsx
if (loading) return <Spin size="large" />;
if (error) return <Alert type="error" message={error} showIcon />;
if (data.length === 0) return <Empty description="Nenhuma solicitação encontrada" />;
return <Table dataSource={data} columns={columns} />;
```
