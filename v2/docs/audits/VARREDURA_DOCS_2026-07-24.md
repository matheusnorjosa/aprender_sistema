---
title: Varredura documental pós-auditoria M00–M28
status: historical
last_verified: 2026-07-24
sources_of_truth:
  - v2/docs/audits/ACHADOS_REAIS.md
  - reverificação por leitura de código contra main d08acfa5 (2026-07-24)
owner: docs
related:
  - ./ACHADOS_REAIS.md
  - ../specs/INDEX_SDD.md
  - ../../../docs/architecture/project-decisions/ADR-018-pull-based-deploy.md
---

# Varredura documental — 2026-07-24

Varredura completa de `v2/docs/` e `docs/` à luz do que a auditoria modular M00–M28 provou.
Base: `main d08acfa5`; produção `v2026.07.18-94f2765` (`94f27651`).

**Escopo do que foi feito:** só documentação. Nenhum arquivo de aplicação, teste, workflow,
compose ou script foi alterado. `v2/docs/_archive/` não foi tocado. Nada foi enviado: sem
push, sem PR, sem issue criada ou comentada.

**Regra que guiou as correções:** a spec descreve **o que o código faz hoje**, e sinaliza
explicitamente onde isso diverge da regra pretendida, com link para o achado. Comportamento
desejado nunca foi escrito como se já existisse.

## Como ler este documento

A seção mais importante é [**Precisa de decisão humana**](#precisa-de-decisão-humana). Ela
lista o que **não** foi corrigido de propósito, e por quê.

---

## 1. O drift catalogado (Passo 2)

### 1.1 ADR-018 — escrito de verdade, ADR-010 superseded

**Decisão tomada: escrever o ADR-018**, em vez de reapontar as 13 referências para outro ADR.

Razão: o mecanismo pull-based não é aspiracional, é o que roda. Verificável no repositório
sem depender de produção — `deploy.yaml` tem apenas os jobs `prepare` e `sign` (o job
`deploy` foi deletado em #1516, conforme o próprio cabeçalho `deploy.yaml:3-12`),
`promote.yml` assina o ponteiro no branch `deploy-pointer` atrás do Environment `production`,
e `v2/infra/deployer/` aplica por digest em `127.0.0.1:9443`. Reapontar 13 referências para
um ADR que descreve outro fluxo seria trocar uma mentira por outra.

| Arquivo | O que mudou |
|---|---|
| `docs/architecture/project-decisions/ADR-018-pull-based-deploy.md` | **Novo.** Contexto, decisão em 6 pontos, consequências e riscos residuais aceitos. Registra honestamente que a decisão é de 2026-07-10 e o documento é de 2026-07-24. |
| `ADR-010-deploy-portainer-direct-to-prod.md` | `Accepted` → **`Superseded by ADR-018`**, com aviso no topo e tabela ponto-a-ponto do que foi revogado e do que continua valendo. |
| `project-decisions/README.md` | Índice atualizado; nota sobre a colisão de numeração do ADR-012. |
| `CONTRIBUTING.md:10` | "Merge na `main` dispara deploy de produção" → falso. Corrigido. |
| `v2/docs/specs/infra/README.md:23` | Apontava ADR-010 e listava `ci`/`environments` como "planejado" quando já estavam escritas. |

**Risco que isso quase criou.** `docs/` é publicado como site MkDocs (`mkdocs.yml`) e
`.github/workflows/docs.yml` roda **`mkdocs build --strict`**. Links relativos de `docs/`
para `v2/docs/` **escapam do `docs_dir`**: passam no `check_doc_links.py` (que resolve no
filesystem inteiro) e **quebrariam o build**. Encontrei 6 links assim em
`docs/architecture/frontend.md` e mais alguns que eu mesmo tinha introduzido nos ADRs.
Convenção aplicada em toda a varredura:

- **navegação** para fora do `docs_dir` → URL absoluta do GitHub;
- **citação de caminho de arquivo-fonte** → code span, sem link.

### 1.2 `ci.spec.md:113` — corrigido, e a auditoria errou a metade boa

A spec dizia: *"Sem `makemigrations --check` na CI — migrations não são validadas no gate e
o deploy não aplica migrations automaticamente (manuais em prod)."* As duas metades eram
falsas, mas **não pelo motivo do briefing**.

- O check **existe e roda**: `_backend-test.yml:155-163`, acionado por `ci.yaml:283`
  (`check_migrations: true`) no job `backend-migrate-integrity`.
- **Mas esse job é `[info]`** (`ci.yaml:271`) e **não está no `needs`** do agregador
  `[required] tests` (`ci.yaml:562-566`), que só assere `backend-tests`,
  `backend-typecheck` e `docker-parity-backend`. Ou seja: **model-drift é detectado e
  reportado, mas não bloqueia merge.**
- Pior: o comentário em `ci.yaml:268-270` afirma que o job "é gated pelo required
  `backend-tests` (needs + assert)". Isso **não corresponde** ao `needs:` declarado. É um
  defeito de CI, registrado aqui e não corrigido (não altero workflows).
- O **deploy**, esse sim, aplica migrations: serviço one-shot `migrate`
  (`docker-compose.prod.yml:47`), com `web`/`worker`/`beat` presos a
  `service_completed_successfully`.

### 1.3 `deploy.spec.md` — 6 serviços, e o `/backups` não fica onde o briefing disse

- **"5 serviços" → 6**: faltava o one-shot `migrate` (`docker-compose.prod.yml:47,84,135,171,240,289`).
- **"nenhum volume `/backups`" → falso**, mas a correção precisa de precisão: o bind-mount
  `/var/backups/aprender:/backups` está no serviço **`worker`** (`:234-235`), **não no
  `beat`**. O `beat` não tem volume nenhum (`:279-287`) — e está certo assim: o `beat`
  apenas agenda, quem executa `backup.perform_database_backup` é o `worker`.
- Separei o que o compose **prova** do que exige olhar produção: o mount existir não prova
  que o backup roda (fato **F7**, não verificado; precedente #1537).
- Cabeçalho "pré-go-live, produção sem dados e sem usuários" estava obsoleto: o go-live foi
  em 2026-07-03; hoje são 148 usuários ativos e **1 superuser**.
- Lista de variáveis da `stack.env` marcada como **snapshot datado de 2026-06-19 e não
  reverificado** (fato **F5**).

### 1.4 `API_REFERENCE.md` e `INDEX_DOCUMENTACAO.md`

`API_REFERENCE.md` levaria um consumidor a escrever código quebrado. Além do POST de Área DAT
(o `DATAreaViewSet` é `ReadOnlyModelViewSet`, `views/dat_module.py:72` — escrita devolve 405),
foram corrigidos:

- **~15 rotas que não existem** (`/api/availability/blocks/` → `/api/availability-blocks/`;
  as 4 rotas `/api/gcal/{preview,publish,resync,cancel}/` são actions do `SolicitacaoViewSet`;
  `/api/dat/compras/` → `/api/dat/compras-materiais/`; `/api/healthz/` → `/healthz/`, fora do
  include de `/api/`).
- **Métodos errados**: `approve`/`reject` são **PATCH**, não POST (`views_solicitacao.py:631,676`)
  — POST devolve 405.
- **Classes de permissão fictícias**: `IsSuperintendencia`, `IsControleOrSuper`, `IsDATOrSuper`,
  `IsDAT`. Nenhuma existe no código, e o padrão é **banido pelo `rbac_lint`**
  (`rbac/__init__.py:24-27`).
- Contratos: filtros documentados de `/api/solicitacoes/` não existiam (`filterset_fields` vazio,
  `:153`); a resposta de conflito usa a chave `ok`, não `available`; o envelope de erro
  documentado não é o que o handler emite.

`INDEX_DOCUMENTACAO.md`: data 2026-03-09 → 2026-07-24, e **todos** os números recontados por
comando, com o comando registrado no próprio documento. **42 models** (41 `models.Model` +
`Usuario(AbstractUser)`) — a lista nominal antiga omitia 14 models reais. **51 rotas**
declaradas em `AppRoutes.tsx`. Testes separados por camada e por critério explícito, deixando
claro que são *declarações*, não casos executados. Recontei models e rotas de forma
independente e ambos conferem.

---

## 2. Precisa de decisão humana

Esta é a seção que importa. Nada aqui foi decidido por mim.

### 2.1 Achados da auditoria que o código refuta

Três achados foram confrontados com o código durante a varredura e **não se sustentam como
escritos**. As specs registram o comportamento real; **o texto das issues deveria ser
corrigido antes de virar trabalho**, ou o implementador vai atrás do bug errado.

| Achado | O que a issue diz | O que o código mostra |
|---|---|---|
| **M08-09** (#1664) | "capacidade diária ignora eventos que cruzam a meia-noite" | Eles **não** são ignorados: entram clampados à janela do dia (`availability_service.py:294-302`). O defeito real é outro — o **novo** intervalo é somado **inteiro** ao dia de início (`:305`) e o dia seguinte nunca é avaliado. |
| **M14-02** (#1630) | pressupõe `MonthlyAvailabilityView.permission_classes = [IsAuthenticated]` | É `[IsAuthenticated, CanViewAllAvailability \| HasSectorAccess]` (`views_availability_monthly.py:80`). O alcance do achado é menor que o descrito. |
| **M18-06** (épico #1653) | "DRF ignora `page_size`" | Verdadeiro globalmente (`settings.py:485-486`), **mas não no módulo de deslocamentos**, que declara `page_size_query_param` (`views_deslocamento.py:79`). Ali o defeito é de frontend. Tratar o épico como "problema do DRF" corrigiria este módulo no lugar errado. |

Além disso, o percentual do `M18-06` ("até 77% das linhas escondidas") não bate com o cálculo
a partir do código (`PAGE_SIZE=100` vs `<Table>` mostrando 15 → ~85%). Número menor, mas é o
que aparece no título da issue.

**Decisão em jogo:** corrigir o texto das issues #1664, #1630 e #1653 (e o percentual do
#1653), ou aceitar que a fila de trabalho contém três descrições que apontam para o mecanismo
errado. Recomendo corrigir — é barato agora e caro depois.

### 2.2 Retificação já aplicada: o binário `age`

`ACHADOS_REAIS.md` afirmava, no `M26-01`, que *"`command -v age` no container web => MISSING"*
e concluía que o restore precisaria rodar noutro host/imagem.

**Isso está errado, e eu corrigi o documento vivo** (com a evidência ao lado, sem apagar o
texto original). O probe rodou no container `aprender_vmain-web-1`, que usa a imagem de
**desenvolvimento**. A imagem de **produção** instala `age` explicitamente
(`v2/infra/Dockerfile.prod:47-57`, junto com `postgresql-client`), e o comentário do próprio
Dockerfile diz que a ausência era um bug **já corrigido** pelo #1455. Quem não tem `age` é o
`Dockerfile.dev`.

Consequência prática: o contorno manual `age -d -i <chave> <arq> | gunzip | psql` **funciona**
no worker de produção. O `M26-01` continua **P0 e vivo** — o defeito é a ordem das operações
em `restore_db.sh:91`, não a falta do binário.

É a **mesma classe de erro do `M27-05`** (porta 8000): conclusão tirada de um ponto de
observação que não era o ambiente sob análise. Vale como sinal de que a auditoria ainda tem
premissas medidas no lugar errado.

### 2.3 Fatos que dependem de olhar produção (não afirmei nenhum)

| Fato | Por que importa | Como confirmar |
|---|---|---|
| **F7 — o backup roda?** | O wiring existe (mount + fail-closed + gate), mas isso **não prova** que há artefato. Se não houver, o `M26-01` deixa de ser "RTO estourado" e vira **perda de dados**. Precedente: **#1537**, backup que nunca rodou. | `ls -lht /var/backups/aprender` na VM01; `docker compose logs beat \| grep database-backup`; `logs worker \| grep perform_database_backup`. |
| **F7b — existe restore ensaiado?** | A tabela "Último ensaio de restore" ficou **vazia de propósito** em `BACKUP_OPERATIONS.md`. Ninguém pode preenchê-la sem a chave privada. | Drill real em staging. Proposta de cadência: trimestral + após qualquer mudança em `backup_db.sh`/`restore_db.sh`/chave. |
| **F5 — envs reais no Portainer** | 18 achados dependem disso, e é o **único** fato capaz de promover algo a P0 (ex.: `DEBUG=True`). A lista em `deploy.spec.md` é de 2026-06-19. | Export read-only das *Environment variables* da stack. |
| **F1 (resto) — Nginx Proxy Manager** | É `external: true` e **não versionado**. Se ele **anexa** `X-Forwarded-For` em vez de sobrescrever, `M01-01` e `M03-03` sobem para P1 (bypass remoto de lockout/throttle). | Inspecionar a config no próprio NPM. |
| **WAL archiving na VM02** | Decide se o RPO é 5 min ou ~24 h. Hoje `BACKUP_OPERATIONS.md` (SSOT) diz 5 min sem prova. | `pg_stat_archiver` na VM02. |
| **`SENTRY_DSN` ausente** | Vários docs tratam "Sentry off" como fato; vem do snapshot de junho. | Junto com F5. |
| **Ruleset `Protect main`** | É config do GitHub, não arquivo. O inventário de 19 checks `[required]` é o que *deveria* estar ligado. | `gh api /repos/<owner>/<repo>/rulesets`. |

### 2.4 Chave `age` — ponto único de falha do DR

A chave privada vive **apenas** no gerenciador de senhas do mantenedor. Combinado com o censo
(**1 superuser ativo**), perder mantenedor + chave = 148 usuários e todo o banco
irrecuperáveis, **mesmo com backups íntegros**. Documentei; não implementei nada.

Opções: (a) custódia dividida / segundo detentor; (b) **segundo recipient `age`** — `age -r`
aceita múltiplos, permitindo uma chave de recuperação independente; (c) aceitar o risco por
escrito.

Relacionado: o **bus factor de 1 superuser** foi agravado pelo #1567, que tornou a
administração de Grupo×Capability superuser-only. Se essa conta cair, ninguém administra RBAC.

### 2.5 Duplicação `docs/business-rules/` × `v2/docs/specs/domain/`

A regra 1-SSOT do ADR-017 pede que um dos dois vire link para o outro. **Não esvaziei
nada**, porque `mkdocs.yml:82-86` publica os 4 arquivos na navegação do site: reduzi-los a
stubs quebraria 4 páginas publicadas. Corrigi as falsidades nos dois lados e apontei os
resumos para a spec.

- **(a)** Manter dois níveis por design (`docs/` = resumo publicado, `specs/` = contrato
  técnico). É o estado atual. Custo: duplicação parcial e disciplina de sincronizar.
- **(b)** Publicar as specs no site e apontar a nav para elas. **Única opção que satisfaz
  1-SSOT de verdade.** Exige `mkdocs-monorepo`/`!include` ou mover `specs/domain/` para
  dentro do `docs_dir`.
- **(c)** Reduzir a stubs e remover da nav. Quebra links externos existentes.

### 2.6 Colisão de numeração — dois casos

**RF01..RF08 significam coisas diferentes nos dois documentos.** Não é divergência de
detalhe: são duas partições do produto, ambas descrevendo funcionalidade real. RF02..RF06
coincidem; **RF01, RF07 e RF08 colidem** (ex.: RF01 = "Autenticação" em `business-rules/`,
"Importação" em `specs/domain/`). Registrei a colisão nos dois arquivos com aviso de
qualificar a origem ao citar. Renumerar unilateralmente invalidaria referências em issues,
testes e ADRs.

**Dois ADR-012 diferentes:** `docs/architecture/project-decisions/ADR-012-dependency-guardrails.md`
e `v2/docs/adr/ADR-012-sha1-idempotency-hashes.md`. Numerei o ADR-018 na pasta canônica e
deixei a colisão registrada no índice. Opções: renumerar o de `v2/docs/adr/`, ou movê-lo para
a pasta canônica com número livre.

### 2.7 `rbac.spec.md` declara superseder um SSOT gerado

O frontmatter tem `supersedes: [RBAC_NAMING.md, rbac_authorization_matrix.md,
GUIA_ADMIN_RBAC.md]`. Mas `rbac_authorization_matrix.md` é **gerada de
`apps/core/rbac/matrix.py`**, tem gate de CI dedicado (`rbac-doc-drift.yml`) e é citada pelo
ADR-017 como conteúdo gerado. Os três "superseded" continuam vivos e referenciados por código.

**Não editei `rbac_authorization_matrix.md`** justamente por causa do guard de drift.

Opções: (a) mover os 3 de `supersedes` para `related`; (b) arquivar de fato e reapontar o gate
para a spec.

Questão adjacente, mais séria: a §4 da matriz diverge da migration 0080 no caso de
`view_all_availability` (§4 diz `Controle, Gerente`; a 0080/D9 redistribui para
`Controle, DAT`). E, com a decisão D17 (atribuição admin-driven, editável no Django Admin),
**é preciso definir se a matriz descreve o *seed* ou o *estado vivo do banco*** — se for o
vivo, ela não é verificável a partir do repositório.

### 2.8 Defeitos de código encontrados (registrados, não corrigidos)

Conforme instruído, não toquei em código. Estes surgiram durante a varredura:

1. **`ci.yaml:268-270`** — comentário afirma gating que o `needs:` não implementa (§1.2).
2. **`rbac-doc-drift.yml:32-37`** — publica check `[required]` **com `paths` no
   `pull_request`**. É o trap clássico: um PR que não toque `matrix.py` deixa o check
   pendente para sempre. O próprio cabeçalho do workflow admite que ainda não está na branch
   protection.
3. **`v2/frontend/src/pages/Solicitacoes.tsx`** — dead code (~15 KB), nenhum módulo o
   importa, nenhuma rota o alcança. `/solicitacoes/minhas` já cobre a função.
4. **`restore_db.sh:17`** — `BACKUP_DIR` hardcoded, ignora a env var (`backup_db.sh:31` usa
   `${BACKUP_DIR:-/backups}`).
5. **Docstrings mentindo**: `seed_rbac.py:3`, `seed_e2e_users.py:14-17`,
   `views/acoes_notificacao.py:36-40` (cita `IsAdminUser`), `api/deslocamentos.ts:91`.
6. **`v2/infra/Makefile:101-103`** — o alvo `logs` usa `$(SERVICE_WEB)`, não `$(SERVICE)`; o
   próprio help do Makefile documenta `make logs SERVICE=web`, que não funciona.
7. **Offsite S3 não funciona** — nenhum Dockerfile instala `aws`, apesar de a documentação
   afirmar que "já está no Dockerfile".
8. **`M09-05` é decisão de produto, não bug de um lado só.** O backend impede auto-registro
   por Coordenador **de propósito** (#1454, anti-IDOR); a UI exige "Formador" e não oferece o
   próprio usuário. Corrigir só um lado quebra o outro.

### 2.9 Lacuna de tooling

`check_doc_links.py` **não detecta** links de `docs/` que escapam do `docs_dir` — ele resolve
no filesystem inteiro. Foi assim que 6 links que quebrariam o `mkdocs build --strict`
passaram no gate. Escrevi um verificador desses e o usei durante a varredura, mas **não o
adicionei ao repositório**: criar script novo está fora do escopo de uma varredura
documental. Vale considerar incorporá-lo ao `check_doc_links.py`.

---

## 3. Verificado e estava certo

Registrado para evitar re-trabalho na próxima varredura.

**Domínio.** CP-01 (`REQUIRE_DOCKER` + `/.dockerenv` → `sys.exit(1)`), CP-04..CP-07,
PA-01 (`Solicitacao` não sobrescreve `save()`/`clean()`), PA-02 (`policies.py:395-421`),
PA-03, PA-05 (AuditLog nos 4 caminhos), idempotência (`select_for_update`, `skip_locked`,
limite 100), RD-01 (`<`/`>` estritos), RD-02/03, RD-04 (buffer 120; limite exato passa),
RD-06 (`to_local`), RD-07, RD-08.

**Backend.** `notificacoes.spec.md` é a spec mais fiel do conjunto — 20/20 itens conferidos.
`stable_import_hash` (SHA1/`|`/UTF-8), `PROTECTED_FIELDS`, ASQ-005, ausência de
`apps.dat_ingest`, os 14 arquivos de GCal, idempotência e 404-como-sucesso,
`conferenceDataVersion=1`, Fernet obrigatório em prod, 11/11 AuditLog actions, db_tables e
constraints do DAT, `REGIAO_UFS` batendo backend×frontend, os 15 comandos de `dev_tools`.
Todos os `sources_of_truth` das 20 specs existem.

**Frontend.** Semântica do `useGoogleGuard` linha a linha, `API_BASE`, estratégia CSRF em 3
passos, retry 1x, 204 → `undefined`, `buildUrl`, 15 diretórios em `pages/`, os 6 redirects
legados, invariante OWASP do fallback genérico do `RequirePolicy`.

**Infra.** `promote.yml` gated no Environment `production`, cosign keyless, `deploy-pointer`,
rejeição de `latest`, aplicação por digest em `127.0.0.1:9443`, `dependency-guardrails` 1-a-1
com `.importlinter`, `ci-security-checks` (3 nomes exatos), rate limits de
`SLO_DEFINITIONS.md` §4.2, `/metrics` gated.

**Ambiente.** Python 3.12 no runtime empacotado, Django 5.2 LTS, DRF 3.17, PostgreSQL 15,
Redis 7, gate de cobertura 85%, pyright `strict`.

---

## 4. Candidatos a arquivamento

Nenhum arquivo foi movido — `_archive/` é imutável e mover exige decisão do dono.

| Documento | Justificativa |
|---|---|
| `docs/operations/ci-backend-xdist-canary.md` + `ci-backend-xdist-stabilization-backlog.md` | **O mais forte.** Documentam experimento **concluído em 2026-06-19**: o xdist já está no gate (`ci.yaml:231,253`) e os 4 itens do backlog estão `resolved`. Nem estão na nav do mkdocs. Sugestão: arquivar e deixar um parágrafo em `ci-check-policy.md`. |
| `v2/docs/IMPLEMENTACAO_PA.md` | A spec de PA já o marca como legado. Cita `Solicitacao.save()`, o caminho obsoleto `apps/core/models.py:412-436` e uma "PA-02 adaptada (inclui DAT)" que `policies.py:395-421` contradiz. Nada nele sobrevive à spec. |
| `v2/docs/reports/*_2026-03-06.md` + `CLASSIFICACAO_PUBLICO_PRIVADO_2026-03-09.md` | Fotografias datadas de março; o backlog e as estimativas foram substituídos na prática pelo `ACHADOS_REAIS.md`. Manter na pasta viva sugere que aquela fila ainda vale. |
| `v2/docs/issues/security_hardening_2026-03-09/` (11 arquivos) | Programa concluído, com resíduo em SEC-011/012 que **nem está nessa pasta**. Arquivar e migrar o resíduo para issues do GitHub. |
| `v2/docs/audits/2026-07-17-system-module-audit.md` | Já **declarado histórico e imutável** pelo `ACHADOS_REAIS.md`; nesta varredura o frontmatter foi corrigido (`draft` → `historical`) e o cabeçalho passou a avisar que suas severidades estão substituídas. Movê-lo para `_archive/` tornaria a regra "não citar severidade dele" estrutural em vez de apenas escrita. |
| `v2/docs/SCALING.md` | Depois das correções, ~60% é exemplo hipotético (K8s, LB e `replicas` inexistentes). Um leitor apressado conclui que há Kubernetes em produção. O conteúdo útil cabe em `RUNBOOK.md` + `DEPLOY_CHECKLIST.md`. Arquivar exige reapontar `ADR-014`, `OBSERVABILITY.md` e `SLO_DEFINITIONS.md`. |
| `v2/docs/SLO_DEFINITIONS.md` §2 e §3 | Tabelas de latência e disponibilidade **sem nenhuma fonte de medição**, inalteradas desde 2026-01-12. Mantidas com banner "alvo, não medido". Se o scraper não for confirmado, viram candidatas. |
| `docs/operations/go-live.md` | Checklist **pré**-go-live de um go-live que já ocorreu (2026-07-03). A parte viva duplica o `DEPLOY_CHECKLIST.md`. Marcado como histórico nesta varredura. |
| `docs/api/{models,views,services}.md` | Três arquivos de 3-5 linhas cujo conteúdo é "vá ler `API_REFERENCE.md`". Candidatos a colapsar numa única página; exige editar `mkdocs.yml`. |
| `v2/docs/GUIDE_DR.md` **vs** `DISASTER_RECOVERY.md` | A fronteira original (VM/systemd × Docker) morreu com o cutover. Candidatos a fusão — mas **só depois** que o #1611 for corrigido e o restore voltar a ser uma chamada de script. |
| `v2/.env.example` | Catálogo que nenhum compose carrega, defasado, e que induz exatamente o erro que `configuration.md` cometia. Não é doc; não editei. |

**Não são candidatos**, apesar da aparência: `frontend-functional-matrix.md` (aponta para
fonte executável e para job de CI), `backup-dr.spec.md` (o aviso é que estava errado, não a
spec), `deslocamento.spec.md` (única documentação do gate owner-or-delegate do #1454 —
promovida a `canonical`), `docs/business-rules/*` (enquanto estiverem na nav do mkdocs).

---

## 5. Prova

```
python scripts/check_doc_links.py        -> OK, 0 links quebrados
python scripts/check_doc_frontmatter.py  -> OK, frontmatter válido
```

Ambos são o gate `[required] docs quality (links + frontmatter)` (`docs-quality.yml`).

**Não foi possível rodar `mkdocs build --strict` neste ambiente** (mkdocs não instalado e a
execução de scripts ad-hoc é bloqueada). A verificação equivalente foi feita estaticamente:
nenhum link relativo em `docs/` escapa do `docs_dir` nem aponta para alvo inexistente.
Recomendo rodar o build antes de publicar.
