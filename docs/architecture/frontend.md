# Frontend

> **SSOT:** este documento **não** duplica o inventário de páginas, os guards de rota nem o
> contrato dos clientes HTTP. Isso vive nas specs vivas (ADR-017, regra de 1 SSOT por tópico):
>
> - **Páginas, rotas e guards** → [`v2/docs/specs/frontend/pages.spec.md`](https://github.com/matheusnorjosa/aprender_sistema/blob/main/v2/docs/specs/frontend/pages.spec.md)
> - **Hooks de RBAC e guards** → [`v2/docs/specs/frontend/hooks-rbac.spec.md`](https://github.com/matheusnorjosa/aprender_sistema/blob/main/v2/docs/specs/frontend/hooks-rbac.spec.md)
> - **Clientes de API, CSRF e sessão** → [`v2/docs/specs/frontend/api-clients.spec.md`](https://github.com/matheusnorjosa/aprender_sistema/blob/main/v2/docs/specs/frontend/api-clients.spec.md)
>
> Os links acima são absolutos porque `v2/docs/` fica **fora** do `docs_dir` do site MkDocs —
> um link relativo daqui quebraria o `mkdocs build --strict`.
>
> A tabela de rotas e a seção de autenticação que existiam aqui estavam desatualizadas
> (ex.: `/solicitacoes`, que não é uma rota registrada). Foram removidas em vez de mantidas
> em duas versões divergentes.

## Stack

Conferido em `v2/frontend/package.json` (2026-07-24):

- **React 18** (`react` 18.3.1) com hooks
- **Vite 7** (`vite` 7.3.5) para build e dev server
- **Ant Design 5** (`antd` 5.27.4) para componentes UI
- **Tailwind CSS 3** (`tailwindcss` 3.4.18) para utilitários
- **React Router 7** (`react-router-dom` 7.15.0)
- **TypeScript 5** (`typescript` 5.9.3); testes com Vitest + MSW, E2E com Playwright
- **Sem `axios`** — o transporte é `fetch()` nativo (ADR-013; detalhe na spec de clientes de API)

## Estrutura

```
src/
├── pages/              # 15 diretórios de domínio (inventário na pages.spec.md)
├── components/         # Componentes reutilizáveis
│   └── access/         # RequirePolicy — guard único de rota
├── api/                # config.ts (wrapper fetch) + 15 clientes temáticos
├── hooks/              # React hooks customizados (RBAC na hooks-rbac.spec.md)
├── constants/          # timing.ts, layout, etc.
└── utils/              # Utilitários
```

## Sessão

Autenticação é por sessão Django com cookie + CSRF em toda mutação — o contrato do lado do
cliente está em [`api-clients.spec.md`](https://github.com/matheusnorjosa/aprender_sistema/blob/main/v2/docs/specs/frontend/api-clients.spec.md).
O tempo de vida da sessão tem default de 2 horas
(`SESSION_COOKIE_AGE`, `v2/backend/config/settings.py:333`), mas é sobrescrito por variável
de ambiente; o valor efetivo em produção depende de verificação humana no Portainer.

## Componentes chave (não cobertos por spec)

### RemoteSelect

Select com busca remota paginada para entidades
(`v2/frontend/src/components/RemoteSelect.tsx`).
Props principais: `fetchOptions`, `renderLabel`, `placeholder`, `disabled`, `mode`, `value`,
`onChange`, `debounceMs`, `extraParams`.

```jsx
<RemoteSelect
  fetchOptions={fetchMunicipios}
  renderLabel={(item) => item.nome}
  placeholder="Selecione um município"
/>
```

### MeetLink

Exibe link do Google Meet
(`v2/frontend/src/components/MeetLink.tsx`); prop única
`href?: string | null`.

```jsx
<MeetLink href={solicitacao.meet_link} />
```

## Regressão frontend↔backend

Casos críticos versionados em
[`frontend-functional-matrix.md`](./frontend-functional-matrix.md).
