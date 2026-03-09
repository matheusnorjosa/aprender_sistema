# Plano de Execução — Estabilização do Sistema v2 (2026-02-23)

**Data**: 2026-02-23
**Base**: análise rigorosa de execução real (backend, frontend, CI, docker, smoke HTTP)
**Objetivo**: voltar o sistema para trilha de entrega segura via processo oficial (issue -> branch -> PR -> CI verde -> merge)
**Epic GitHub**: #620

---

## 1) Regras de execução (processo oficial)

1. Trabalhar uma issue por vez.
2. Cada issue deve ter branch e PR próprios.
3. PR só é elegível para merge com CI verde.
4. Sem “batch fixes” fora de issue/prioridade definida.
5. Sempre validar em execução real (não apenas leitura de código).

---

## 2) Estado atual validado (23/02/2026)

### Backend
- Suite completa: `1706 passed`, `30 skipped`, `2 failed` (OAuth tests).
- Falhas atuais: `apps/core/tests/test_google_oauth.py` (mocks/sensibilidade de ambiente).
- Health: `readyz` e `healthz` funcionando.

### Fluxos críticos
- Solicitações (`create -> approve/reject`) funcionando via HTTP real.
- RBAC principal validado por perfil.
- Import de compras funcionando (dry-run).
- Import de ações/cadastros quebrados com `500` por assinatura incorreta (`path` vs `file_path`).

### Frontend
- `lint`, `typecheck`, `build` passam.
- `size` falha (bundle acima do limite).
- Unit tests passam em container, mas falham no host por timeout de pool.
- E2E não roda no host/container atual (dependências/browser runtime).

### Qualidade estrutural
- Rotas E2E divergentes das rotas reais do app.
- `makemigrations --check --dry-run` aponta renomeações pendentes de índices.
- `continue-on-error: true` presente em checks relevantes do frontend CI.

---

## 3) Sequência de execução (por prioridade)

## P0 — Estabilização imediata de entrega

### P0.1) Corrigir falha de CI no PR aberto (#610)
- Escopo:
  - Corrigir testes OAuth quebrados por patch incorreto/sensibilidade de ambiente.
  - Garantir backend suite verde no PR.
- Critérios de aceite:
  - `pytest apps -q` sem falhas.
  - PR #610 com job `tests` verde.
- Dependência: nenhuma.
- Issue: `#611`.

### P0.2) Corrigir 500 nos imports críticos
- Escopo:
  - `POST /api/controle/import-acoes/`.
  - `POST /api/dat/import-cadastros/`.
  - Ajuste de chamada/sinatura (`file_path`) + testes de endpoint.
- Critérios de aceite:
  - Ambos endpoints retornam `200` em `dry_run=true` com CSV mínimo válido.
  - Sem regressão em `test_import_endpoints.py` e testes ETL relacionados.
- Dependência: nenhuma.
- Issue: `#612`.

### P0.3) Corrigir contrato e agregação do Mapa Brasil
- Escopo:
  - Eliminar dupla agregação UF no frontend.
  - Não misturar `compras` em métrica de `eventos`.
  - Implementar filtros de data de ponta a ponta (`data_inicio/data_fim`).
- Critérios de aceite:
  - Totais consistentes entre backend e frontend.
  - Filtro de data altera resultado de forma verificável.
  - Testes backend/frontend adicionados ou atualizados.
- Dependência: nenhuma.
- Issues: `#577`, `#578`, `#579`, `#613`.

---

## P1 — Confiabilidade de testes e pipeline

### P1.1) Alinhar rotas E2E com rotas reais do app
- Escopo:
  - Atualizar specs Playwright que ainda usam rotas legadas (`/admin-dat`, `/dat-module/*`, etc.).
- Critérios de aceite:
  - Specs navegam para rotas existentes no `App.tsx`.
- Dependência: nenhuma.
- Issue: `#614`.

### P1.2) Corrigir ambiente de execução E2E (host + container)
- Escopo:
  - Resolver dependências de browser (host).
  - Garantir browsers instalados no container frontend.
- Critérios de aceite:
  - `npm run test:e2e -- --project=chromium` executa setup sem falha de runtime.
- Dependência: P1.1.
- Issue: `#615`.

### P1.3) Endurecer frontend CI para evitar falso verde
- Escopo:
  - Revisar/remover `continue-on-error` em etapas críticas (`test`, `size`, checklist).
- Critérios de aceite:
  - Falha real de teste/bundle quebra pipeline.
- Dependência: P1.1/P1.2 para evitar quebrar pipeline por configuração incompleta.
- Issue: `#616`.

### P1.4) Ajustar Makefile operacional
- Escopo:
  - Corrigir alvo inexistente `seed_demo_users`.
  - Corrigir path de E2E targets.
- Critérios de aceite:
  - Targets executam sem erro de comando/caminho inexistente.
- Dependência: nenhuma.
- Issue: `#617`.

---

## P2 — Higiene técnica e idempotência operacional

### P2.1) Corrigir idempotência do `seed_e2e_users`
- Escopo:
  - Evitar quebra por conflito de município único em reexecuções.
  - Garantir que reexecução não cancele criação/atualização de usuários por rollback total.
- Critérios de aceite:
  - Rodar comando duas vezes consecutivas com resultado estável.
- Dependência: nenhuma.
- Issue: `#618`.

### P2.2) Resolver pendências de migration check
- Escopo:
  - Gerar/aplicar renomeações de índices pendentes (`core`, `dat_ingest`).
- Critérios de aceite:
  - `makemigrations --check --dry-run` sem pendências.
- Dependência: nenhuma.
- Issue: `#619`.

---

## 4) Ordem prática de execução em PRs

1. #611
2. #612
3. #613 (+ fechamento técnico de #577/#578/#579)
4. #614
5. #615
6. #617
7. #618
8. #619
9. #616

---

## 5) Critério de encerramento do ciclo

- Sem falhas na suite backend principal.
- Imports críticos funcionando em smoke real.
- Mapa Brasil com dados consistentes e filtros funcionais.
- E2E executável (ao menos setup+smoke) em ambiente definido.
- CI sem permissividade indevida em checks críticos.
