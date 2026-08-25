# Reference — AS v2 Domain UI Patterns

## Timezone display (CP-03)

Storage is UTC; always render in `America/Fortaleza`. The canonical setup lives in
`v2/frontend/src/components/DateTimeRange.tsx`, which calls
`dayjs.tz.setDefault('America/Fortaleza')` after extending the utc/timezone plugins.

```tsx
import dayjs from 'dayjs';
import utc from 'dayjs/plugin/utc';
import timezone from 'dayjs/plugin/timezone';

dayjs.extend(utc);
dayjs.extend(timezone);

dayjs(solicitacao.inicio).tz('America/Fortaleza').format('DD/MM/YYYY HH:mm');
```

## Solicitação wizard steps

`v2/frontend/src/pages/Solicitacoes/NewSolicitacaoWizard.tsx`:

```tsx
import { Steps } from 'antd';
<Steps current={currentStep}>
  <Steps.Step title="Projeto" />
  <Steps.Step title="Data e Local" />
  <Steps.Step title="Formadores" />
  <Steps.Step title="Revisão" />
</Steps>
```

## Approval flow (PA-01 a PA-07)

Gate approval controls on the permission flag — never render Aprovar/Recusar to users who
can't approve:

```tsx
{permissions.pode_aprovar_superintendencia && (
  <Space>
    <Button type="primary" onClick={handleApprove}>Aprovar</Button>
    <Button danger onClick={handleReject}>Recusar</Button>
  </Space>
)}
```

## Availability / conflict codes (RD-01 a RD-08)

SSOT for codes, labels and Tailwind classes is `v2/frontend/src/pages/Disponibilidade/codes.ts`
(`AvailabilityCode`, `CODE_LABEL`, `CODE_CLASS`). Reuse it — do not redefine a parallel
color map. The real codes are:

| Code | Meaning |
|------|---------|
| `E`  | 1 evento |
| `2`  | ≥2 eventos |
| `P`  | Bloqueio parcial |
| `T`  | Bloqueio total |
| `X`  | Evento + bloqueio |
| `D`  | Deslocamento |
| `D1` | Evento + deslocamento |
| `''` | Célula sem código |

```tsx
import { CODE_LABEL, CODE_CLASS, type AvailabilityCode } from '../pages/Disponibilidade/codes';

<span className={CODE_CLASS[code]}>{CODE_LABEL[code]}</span>
```
