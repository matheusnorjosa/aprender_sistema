# Plano Mestre - Remocao Definitiva do ETL Backend (sem quebra)

Data: 2026-03-24  
Status: Aprovado para execucao incremental  
Escopo tecnico: Backend (`v2/backend`) + CI/CD + documentacao operacional  
Escopo funcional: manter importacao via paginas de importacao do sistema e remover dependencia do app legado `apps.dat_ingest`.

## 1. Objetivo
Remover o ETL legado do backend de forma definitiva, sem regressao de negocio e sem downtime, garantindo:
- sem rotas ETL expostas;
- sem dependencia de `apps.dat_ingest` no runtime;
- sem comandos ETL legados em operacao;
- sem perda de capacidade de importacao (fluxo oficial passa a ser pelas paginas/API de importacao do modulo principal);
- trilha de auditoria e rollback controlado durante a transicao.

## 2. Escopo e limites
## Inclui
- desativacao e remocao progressiva de `apps.dat_ingest`;
- limpeza de referencias ETL em `settings`, `urls`, comandos e CI;
- migracao final das responsabilidades para `apps.core.services.*` (imports oficiais);
- atualizacao de testes e documentacao.

## Nao inclui
- reescrever regras de negocio das importacoes ja consolidadas no `core` (a nao ser ajuste de compatibilidade);
- mudancas de UX alem das ja necessarias para manter o fluxo de importacao vigente.

## 3. Estado atual (AS-IS resumido)
Evidencias no codigo:
- `config/settings.py` ainda controla `INCLUDE_ETL` e pode instalar `apps.dat_ingest`.
- `config/urls.py` ainda registra rotas ETL condicionalmente (`/api/etl/reports/latest/` e namespace `dat-v1`).
- `apps/dat_ingest/*` contem app, modelos staging, views, urls, comandos e testes.
- Existem testes/documentacao que assumem ETL opcional (`test_optional_etl.py`, docs/scripts).
- Parte da logica de importacao ja foi movida para `apps/core/services` (base para desligamento seguro).

Risco principal:
- remover tudo de uma vez pode quebrar ambientes que ainda tenham `INCLUDE_ETL=true` ou uso de comandos antigos.

## 4. Estrategia de execucao (sem quebra)
Modelo em 3 estagios:
1. **Desligar em runtime** (feature toggle -> default OFF em todos os ambientes ativos).
2. **Garantir substituicao funcional** (imports oficiais no core com testes e smoke em dev/staging).
3. **Eliminar codigo legado** (app/dat_ingest, comandos, testes e docs legados).

## 5. Frentes de trabalho (com criterios de aceite)

## F0 - Baseline, inventario e gate de seguranca
### Entregas
- inventario tecnico de todos os pontos ETL (codigo, CI, docs, runbooks);
- matriz "legado -> substituto" por endpoint/comando;
- checklist de rollback operacional.

### Criterios de aceite
- lista completa de referencias ETL validada em PR (backend/frontend/ci/docs);
- mapeamento com owner por item;
- nenhum item "sem substituto" para fluxo critico.

### Testes esperados
- n/a (fase documental), mas com evidencia de comandos de busca (`rg`).

---

## F1 - Kill switch e hard-disable de runtime
### Entregas
- `INCLUDE_ETL` default passa para `false`.
- `config/urls.py` deixa de expor rotas ETL por padrao.
- healthcheck/startup sem dependencia de `apps.dat_ingest`.
- smoke em dev e staging com ETL desativado.

### Criterios de aceite
- `apps.dat_ingest` nao aparece em `INSTALLED_APPS` com config padrao;
- `/api/etl/reports/latest/` retorna `404`;
- login, dashboard e fluxos de importacao oficiais continuam funcionando.

### Testes esperados
- backend:
  - `pytest apps/core/tests/test_optional_etl.py -q` (atualizado para novo comportamento default);
  - suite de importacao oficial (`core/services/*import*`).
- smoke manual dev/staging:
  - autenticar;
  - listar/importar em `/controle/*` e `/dat/*` (paginas oficiais de importacao);
  - validar ausencia de erro 500 em startup.

---

## F2 - Contrato de importacao oficial (substituicao completa)
### Entregas
- consolidar APIs/import services oficiais no `apps.core`;
- remover qualquer chamada de frontend/backend para endpoint ETL legado;
- garantir auditoria de importacao (usuario, arquivo, ano, resultado) no fluxo oficial.

### Criterios de aceite
- nenhuma rota frontend ativa consome `api/etl/*`;
- nenhuma acao operacional depende de comando `etl_*` do app legado;
- importacoes continuam idempotentes e auditaveis.

### Testes esperados
- testes backend dos servicos de importacao (`test_etl_dat_cadastros.py`, `test_etl_acoes_controle.py` ou equivalentes renomeados);
- testes de API das paginas de importacao;
- build/lint frontend verde.

---

## F3 - Remocao de codigo legado `apps.dat_ingest`
### Entregas
- remover app `v2/backend/apps/dat_ingest` do repositorio;
- remover imports, scripts e comandos legados ligados ao app;
- ajustar pyright/pytest/cobertura para nova estrutura;
- remover rotas/namespace dat-v1 residuais.

### Criterios de aceite
- busca por `apps.dat_ingest` retorna 0 em codigo ativo (exceto changelog/arquivo historico); 
- `manage.py check` e migracoes executam sem o app;
- CI backend completo verde.

### Testes esperados
- `pytest` backend completo (ou matriz acordada de suites criticas);
- `pyright apps/core config` sem referencia a `apps/dat_ingest`;
- `black/isort/flake8` verdes.

---

## F4 - Banco e dados legados (staging tables/logs)
### Entregas
- plano de retencao para tabelas legado `dat_ingest_*`;
- migration de cleanup (drop tables) somente apos janela de seguranca;
- backup + procedimento de restore documentado antes do drop.

### Criterios de aceite
- backup confirmado antes de drop;
- migration reversivel quando aplicavel;
- zero consulta da aplicacao para tabelas removidas.

### Testes esperados
- migrate up/down em ambiente de homologacao;
- smoke de funcionalidades principais apos migration;
- verificacao SQL de ausencia de tabelas legadas apos rollout final.

---

## F5 - CI/CD, observabilidade e docs finais
### Entregas
- remover jobs/checks ETL legados da pipeline;
- atualizar runbooks, README e docs de operacao/importacao;
- adicionar alerta para tentativa de uso de endpoint/comando removido (mensagem deprecada clara no periodo de transicao, se necessario).

### Criterios de aceite
- nenhum workflow referencia ETL legado;
- docs oficiais descrevem apenas fluxo de importacao atual;
- operadores conseguem executar importacao sem comandos ETL antigos.

### Testes esperados
- workflows principais verdes em PR e main;
- dry-run de runbook atualizado em dev/staging.

## 6. Ordem recomendada de rollout
1. F0
2. F1
3. F2
4. F3
5. F4
6. F5

## 7. Plano de rollback
- Janela F1-F2: rollback simples via revert do PR (reabilita toggle/rotas).
- Janela F3: rollback via revert do commit de remocao (antes de F4).
- Janela F4 em diante: rollback depende de restore de backup para tabelas dropadas.

Regra operacional:
- **nao executar F4 antes de pelo menos 1 ciclo completo de uso estavel em staging e 1 ciclo em producao sem consumo ETL legado**.

## 8. Metricas de sucesso
- 0 chamadas em producao para `api/etl/*` por 14 dias.
- 0 execucoes de comandos `etl_*` por 14 dias.
- 100% dos imports operacionais executados pelas paginas/API oficiais.
- 0 incidentes SEV1/SEV2 ligados a importacao apos remocao.

## 9. Checklist global de aceitacao
- [ ] ETL legado desativado em runtime padrao.
- [ ] Fluxos de importacao oficiais validados em dev e staging.
- [ ] Codigo `apps.dat_ingest` removido.
- [ ] Tabelas legadas tratadas com backup + janela segura.
- [ ] CI/CD e docs sem referencias legadas.
- [ ] Runbook de operacao e rollback atualizado.

## 10. Rastreabilidade (issues)
Epic principal: #967  
Subissues:
1. #968 - F0 - Inventario e matriz legado->substituto
2. #969 - F1 - Hard-disable runtime ETL (settings/urls)
3. #970 - F2 - Consolidacao do contrato de importacao oficial
4. #971 - F3 - Remocao do app/dat_ingest e dependencias
5. #972 - F4 - Cleanup de banco (tabelas legadas) com backup
6. #973 - F5 - CI/CD + documentacao final sem ETL

> Todas as issues devem apontar para este plano e conter:
> - escopo tecnico;
> - criterios de aceite (copiados literalmente da secao da fase);
> - testes esperados.
