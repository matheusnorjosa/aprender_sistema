# Plano de Migração: Axios → Fetch API Nativa

**Epic:** #1039
**Issue original:** #782 (ASQ-009: Unificar cliente HTTP frontend)
**ADR:** ADR-013-axios-pinning-fetch-migration
**Status:** Planejado
**Data:** 2026-03-31
**Branch:** `feat/remove-axios-fetch-migration`

## Issues

| Fase | Issue | Descrição |
|------|-------|-----------|
| 0 | #1040 | Preparação: helpers em config.ts |
| 1 | #1041 | Migrar acoesNotificacao.ts |
| 2 | #1042 | Migrar adminDAT.ts |
| 3 | #1043 | Migrar datModule.ts |
| 4 | #1044 | Migrar hooks e componentes |
| 5 | #1045 | Remover axios do projeto |

---

## 1. Contexto

Em 31/03/2026, a conta npm do axios foi comprometida (versões maliciosas 1.14.1 e 0.30.4).
O projeto usa axios 1.13.5 (seguro), pinado em versão exata no PR #1031.

O frontend **já usa um sistema híbrido**: 10 arquivos usam `fetchAPI` (wrapper sobre fetch nativa),
enquanto 3 arquivos de API + 5 hooks/componentes ainda usam a instância axios de `api.ts`.

### Motivação

- **Segurança:** Eliminar dependência com histórico de supply chain attack
- **Bundle:** -40KB (axios + dependências)
- **Consistência:** Unificar em um único padrão HTTP (`fetchAPI`)
- **Manutenção:** Zero risco futuro de vulnerabilidades em lib terceira

---

## 2. Estado Atual

### Já migrado (usa fetchAPI de config.ts) — NÃO TOCAR

| Arquivo | Funções |
|---------|---------|
| `api/auth.ts` | 3 |
| `api/availability.ts` | 8 |
| `api/dashboard.ts` | 1 |
| `api/gcal.ts` | 11 |
| `api/lookup.ts` | 7 |
| `api/solicitacoes.ts` | 18 |
| `api/stats.ts` | 1 |
| `api/systemConfig.ts` | 2 |
| `api/teamMetrics.ts` | 3 |
| `api/ops.ts` | 17 |

### Precisa migrar

| # | Arquivo | Tipo | Funções | Dificuldade |
|---|---------|------|---------|-------------|
| 1 | `api/acoesNotificacao.ts` | API client | 10 | Baixa |
| 2 | `api/adminDAT.ts` | API client | 29 | Média |
| 3 | `api/datModule.ts` | API client | 67 | Média |
| 4 | `hooks/useGoogleIntegration.ts` | Hook | 2 | Baixa |
| 5 | `hooks/useSessionMonitor.ts` | Hook | 1 | Baixa |
| 6 | `hooks/useDebouncedOptions.ts` | Hook | 1 | Baixa |
| 7 | `components/google/GoogleIntegrationCard.tsx` | Componente | 2 | Baixa |
| 8 | `services/preloadSearchData.ts` | Service | 4 | Baixa |
| 9 | `api.ts` | **DELETAR** | — | — |
| 10 | `package.json` | **uninstall axios** | — | — |

---

## 3. Infraestrutura Existente (já pronta)

### fetchAPI (config.ts)

- CSRF token injection automático para POST/PUT/PATCH/DELETE
- Retry automático em 403 CSRF (1 tentativa)
- Credentials: include (session cookies)
- Error handling com status code no objeto Error
- `response.json()` automático (retorna `T` direto)

### buildUrl (config.ts)

- Constrói URL com query params
- Filtra null/undefined/empty
- Já usado por 10 arquivos

### getErrorStatus (errors.ts)

- Extrai status de erros axios E fetch
- Já suporta ambas as shapes

### deduplicatedFetch (request.ts)

- Previne requests concorrentes duplicados
- Usado nos hooks de polling

---

## 4. Fases de Implementação

### Fase 0: Preparação (config.ts) — #1040

Adicionar dois helpers em `api/config.ts`:

1. **`fetchBlob(url, options)`** — para download de arquivos (CSV export)
2. **`fetchWithErrorMapping<T>(url, options, errorMap)`** — preserva mensagens de erro customizadas

### Fase 1: Migrar acoesNotificacao.ts — #1041

Padrão de transformação:

```text
api.get(url, { params }) → fetchAPI(buildUrl(url, params))
api.post(url, data) → fetchAPI(url, { method: 'POST', body: JSON.stringify(data) })
```

Remover: `apiRequest` wrapper, imports de `AxiosResponse`, import de `api`

### Fase 2: Migrar adminDAT.ts — #1042

Mesmo padrão + preservar error mapping:

- 403 → "Você não tem permissão para realizar esta ação."
- 404 → "Recurso não encontrado."
- Backend `errors` field → extrair primeiro erro

### Fase 3: Migrar datModule.ts — #1043

Mesmo padrão + caso especial blob:

- `exportDATRegistros` usa `responseType: 'blob'` → migrar para `fetchBlob()`
- Error map: 403 → "Acesso restrito ao setor DAT."

### Fase 4: Migrar hooks e componentes — #1044

5 arquivos com chamadas diretas a `api.*`:

- Trocar `api.get/post` por `fetchAPI`
- Error handling: `axiosError.response?.data?.error` → `(error as Error).message`
- `response.data` → retorno direto de `fetchAPI`

### Fase 5: Remover axios — #1045

1. Deletar `src/api.ts`
2. `npm uninstall axios`
3. Verificar zero imports restantes
4. Verificar bundle size

---

## 5. Arquivos Tocados (completo)

| Ação | Arquivo |
|------|---------|
| Editar | `src/api/config.ts` |
| Editar | `src/api/acoesNotificacao.ts` |
| Editar | `src/api/adminDAT.ts` |
| Editar | `src/api/datModule.ts` |
| Editar | `src/hooks/useGoogleIntegration.ts` |
| Editar | `src/hooks/useSessionMonitor.ts` |
| Editar | `src/hooks/useDebouncedOptions.ts` |
| Editar | `src/components/google/GoogleIntegrationCard.tsx` |
| Editar | `src/services/preloadSearchData.ts` |
| Editar | `src/api/__tests__/adminDAT.test.ts` |
| Editar | `src/api/__tests__/datModule.test.ts` |
| Editar | `src/hooks/__tests__/useGoogleIntegration.test.js` |
| Editar | `src/hooks/__tests__/useSessionMonitor.test.js` |
| **Deletar** | `src/api.ts` |
| Editar | `package.json` |

**Total: 14 edições + 1 deleção**

---

## 6. Riscos e Mitigações

| Risco | Prob. | Impacto | Mitigação |
|-------|-------|---------|-----------|
| Error handling divergente | Média | Alto | `fetchWithErrorMapping` preserva mensagens |
| CSRF token regression | Baixa | Alto | fetchAPI já testado em 10 arquivos prod |
| Blob download quebra | Baixa | Médio | `fetchBlob` dedicado + teste manual |
| Testes quebrados | Alta | Baixo | Atualizar mocks em cada fase |
| FilterParams → QueryParams | Média | Médio | Tipos são compatíveis |

---

## 7. Estratégia de Testes

### Por fase

- **Fase 0:** Testes unitários para fetchBlob e fetchWithErrorMapping
- **Fases 1-3:** `npx vitest src/api/` após cada arquivo
- **Fase 4:** `npx vitest src/hooks/ src/components/`
- **Fase 5:** Full test suite + build

### Smoke test manual (pós-migração)

- [ ] Login/logout funciona
- [ ] CSRF token obtido automaticamente
- [ ] CRUD de DAT registros
- [ ] Export CSV do DAT (blob)
- [ ] Admin: criar/editar usuário
- [ ] Notificações: listar/marcar lida
- [ ] Google Calendar: status + selecionar calendário
- [ ] Session monitor: renovar sessão
- [ ] InstantSearch: resultados aparecem

---

## 8. Commits (Conventional Commits)

```text
feat(frontend): add fetchBlob and fetchWithErrorMapping helpers          (#1040)
refactor(frontend): migrate acoesNotificacao from axios to fetchAPI      (#1041)
refactor(frontend): migrate adminDAT from axios to fetchAPI              (#1042)
refactor(frontend): migrate datModule from axios to fetchAPI             (#1043)
refactor(frontend): migrate hooks and components from axios to fetchAPI  (#1044)
chore(frontend): remove axios dependency (-40KB bundle)                  (#1045)
```

---

## 9. Referências

- Issue #782 (ASQ-009)
- ADR-013-axios-pinning-fetch-migration
- PR #1031 (pin axios 1.13.5)
- CVE-2025-27152
