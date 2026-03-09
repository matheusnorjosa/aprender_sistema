# Analise Tecnica - Caminho Canonico da API (2026-03-06)

## Objetivo

Definir um unico caminho canonico para a API do sistema v2 com base em evidencias de uso real, risco operacional e custo de migracao.

## Escopo da analise

- Backend (roteamento, settings, schema OpenAPI)
- Frontend (clientes API e service worker)
- Testes e automacoes (Playwright, Locust, Makefile)
- Infra e documentacao operacional

## Metodologia

1. Inventario de rotas reais via OpenAPI (`/api/schema/?format=json`).
2. Validacao de paridade entre prefixos `/api/` e `/api/v1/`.
3. Mapeamento de consumo first-party (frontend e testes).
4. Levantamento de referencias remanescentes a `/api/v1/` no repositorio.
5. Matriz de decisao com criterios objetivos.

## Achados (dados objetivos)

### 1) Superficie de API atual

- `139` paths em `/api/*`
- `139` paths em `/api/v1/*`
- Paridade: `0` faltas de espelho entre os dois prefixos

Interpretacao:
- Hoje existe duplicidade de **superficie HTTP** por design.
- Nao existe evidência de duplicidade de implementacao de negocio; o mesmo conjunto de views e exposto em dois prefixos.

### 2) Distribuicao por dominio (prefixo `/api/`)

Top dominios por quantidade de paths:

- `dat`: 35
- `gcal`: 15
- `solicitacoes`: 12
- `options`: 8
- `metrics`: 5
- `controle`: 4
- `integrations`: 4
- `lookup`: 4
- `reports`: 4

Observacao:
- A distribuicao em `/api/v1/` e identica, reforcando que e um espelho.

### 3) Consumo real do frontend (first-party)

Evidencias:

- Base URL da aplicacao: `VITE_API_URL` default em `/api`
- Clientes em `frontend/src/api/*` fazem chamadas relativas para `/api` via `API_BASE`.
- Nao ha uso funcional de `/api/v1` nos clientes da aplicacao.

Achado relevante:

- `frontend/public/sw.js` ainda usa rotas cacheaveis em `/api/v1/...` (inconsistente com o restante do frontend).

### 4) Consumo real de automacoes e operacao

Evidencias:

- `v2/Makefile`: comandos operacionais usam `/api/...`
- Testes de carga e E2E usam `/api/...`
- Health/readiness operacional usam `/api/readyz/`

Conclusao:

- Todo fluxo first-party de desenvolvimento, teste e operacao ja esta padronizado em `/api`.

### 5) Onde `/api/v1` ainda aparece no codigo (nao-doc)

Ocorrencias relevantes remanescentes:

- `backend/apps/core/tests/test_versioning.py` (testes de compatibilidade)
- `frontend/public/sw.js` (cache offline)
- referencias pontuais de exemplo/comentario em backend (nao fluxo de runtime)

Conclusao:

- `/api/v1` em runtime first-party esta praticamente restrito a compatibilidade e ao service worker.

## Analise de risco

### Risco da situacao atual (duplo canônico implicito)

- Ambiguidade para novos desenvolvedores e para documentacao.
- OpenAPI/Swagger exibindo caminhos duplicados (ruido).
- Maior superficie de manutencao para contratos.
- Maior chance de drift (ex: service worker cacheando prefixo diferente do usado pela app).

### Opcao A - Canonico `/api/`

Pros:

- Alinha com uso real atual de frontend, testes e operacao.
- Menor custo de migracao.
- Menor risco de regressao imediata.
- Reduz confusao de "v2 com rota v1".

Contras:

- Versionamento no path fica menos explicito para futuras breaking changes.

### Opcao B - Canonico `/api/v1/`

Pros:

- Versionamento explicito no path.

Contras:

- Exige migracao coordenada de frontend, testes, automacoes, docs e operacao.
- Aumenta risco de quebra em curto prazo.
- Nao reflete o padrao first-party ja consolidado.

## Decisao recomendada

Adotar oficialmente **`/api/` como caminho canonico** para o sistema v2.

Racional:

1. E o caminho efetivamente usado por consumidores first-party.
2. Minimiza risco e custo de transicao.
3. Resolve a confusao atual sem reescrever toda a operacao.
4. Permite manter `/api/v1/` como alias de compatibilidade por janela controlada.

## Politica de compatibilidade proposta

1. Canonico: `/api/*`
2. Compatibilidade temporaria: `/api/v1/*` (alias)
3. Regra imediata: novos codigos e docs devem usar somente `/api/*`
4. Proxima fase: adicionar telemetria de uso do alias `/api/v1/*`
5. Remocao futura: remover alias somente apos janela com evidencias de nao-uso

## Proximos passos sugeridos (execucao)

1. Documentacao oficial
   - Atualizar referencia e exemplos para `/api/*`.
   - Registrar politica canonica explicitamente.
2. Consistencia frontend
   - Ajustar `service worker` para cachear `/api/*` (nao `/api/v1/*`).
3. Governanca de compatibilidade
   - Criar issue para telemetria de uso de `/api/v1/*`.
4. Desligamento controlado do alias
   - Definir janela (ex.: 30-60 dias) com criterio objetivo de corte.

## Conclusao executiva

O problema nao e "v1 legado ativo de negocio", e sim **duplicidade de prefixo de rotas**.
Com base no uso real do sistema, o caminho canonico tecnicamente mais seguro e coerente hoje e **`/api/`**.

