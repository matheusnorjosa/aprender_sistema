---
status: active
last_verified: 2026-08-25
verified_at_commit: 5801e17d
sources_of_truth:
  - scripts/check_doc_frontmatter.py
  - scripts/check_doc_links.py
  - .github/workflows/docs-quality.yml
  - .github/workflows/rbac-doc-drift.yml
  - .github/workflows/staging-gate-audit.yml
  - .github/pull_request_template.md
  - v2/docs/audits/ACHADOS_REAIS.md
  - v2/backend/scripts/rbac_lint.py
  - v2/backend/apps/core/tests/test_rbac_lint.py
  - v2/backend/scripts/check_agent_instructions.py
  - v2/backend/scripts/check_doc_impact.py
  - v2/backend/scripts/doc_drift_report.py
  - v2/backend/scripts/doc_frontmatter.py
  - .claude/citacoes-apagadas-allowlist.txt
  - .claude/hooks/test_hooks.py
---

# Plano — drift documental

Correção sustentável do drift entre documentação e código.

**Origem:** auditoria de 2026-08-24 (450 arquivos, 5.852 afirmações, 82% conferem,
814 achados, 72 críticos) + investigação de 2026-08-25 sobre por que as defesas
existentes não pegaram nada + análise adversarial de 7 lentes sobre a v1 deste
plano (79 gaps, **15 bloqueantes**).

> [!important] Como este documento não apodrece
> A auditoria encontrou **28 casos de backlog fantasma** nesta mesma pasta.
>
> Regra: **nenhum item vira `feito` sem (a) o comando que prova o comportamento e
> (b) o teste que prova que o gate MORDE.** Rodar o script contra o repo é
> *smoke*, não teste — prova que executa, nunca que reprova. Quando todos
> passarem, este arquivo vai para `_archive/`.

---

## v1 → v2: o que a crítica derrubou

A primeira versão deste plano tinha quatro erros que teriam ido para produção.
Registrados porque a lição vale mais que a correção.

| v1 dizia | Medição | v2 |
|---|---|---|
| «0.1 é um clique, zero código» | `rbac-doc-drift.yml` tem **path filter** e rodou **2× na vida**. Required + path filter = check pendente eterno — o trap que `docs-quality.yml` documenta em comentário | Movido para **último**, e só depois de remover o path filter |
| `git log --since=<last_verified>` | **Não-determinístico.** Approxidate preenche a hora ausente com a **hora atual**: commit das 09:00 não aparece em `--since=hoje` às 09:21; o das 11:00 aparece. E inclui o mesmo dia, então spec corrigida no próprio PR se autoacusa | **Âncora em SHA**, nunca data |
| «20 de 26 specs em drift» | **21 de 21** com `sources_of_truth`. As 5 verdes são exatamente as 5 que **não declaram nada** | Gate precisa detectar `sources_of_truth` **encolhendo** |
| «baseline decrescente compra paz» | **95% das specs baselinadas recebem commit novo em 7 dias.** «Falha se piorar» = falha sempre | Camada 1 vira **relatório**; o gate é por PR |
| «`settings.py` é hub de quase toda spec» | É de 4. Hubs reais: `rbac/policies.py`=8, `core/urls.py`=7 | Lista de hub recalibrada |
| 3.2 e 3.5 (corrigir `.claude/`, `AGENTS.md`) | **Não estão no git.** 155 `.md` em disco, zero rastreados | Vira decisão D3, não item de execução |

---

## O que este repositório prova que funciona

Não é opinião — é o histórico dos gates que pegaram e dos que não pegaram.

**Funciona aqui:**

- **Limpar primeiro, trancar depois com allowlist** — `check-no-legacy-js`
- **Ratchet sobre piso medido**, com margem antiflake — cobertura vitest, subida 3× em 4 dias
- **Auto-teste do gate**, com caso «baseline limpo passa» — `test_rbac_lint.py`
- **Escopo resolvido dentro do job**, nunca por path filter — `staging-gate-scope.sh`
- **Checkbox verificado por máquina no corpo do PR** — **100% de adesão em 25 de 25 PRs**, e o gate nem está no ruleset

**Não funciona aqui:**

- `[required]` no nome sem estar no ruleset — **9 de 19 jobs** estão assim
- **Cron** — `ci-runtime-telemetry` falhou **26 execuções consecutivas** desde 31/07 e ninguém viu

> A conclusão prática para mantenedor solo: **o formato de maior adesão não
> depende de ação de admin.** Bloqueio não é o que faz um gate pegar — formato é.

---

## Ordem de execução

Derivada do que sobreviveu acima. **A ordem é parte do plano**, não sugestão: a
v1 falhava por começar pelo item que congela a `main`.

```
2.2 + Camada 3   limpar o dado sujo
       ↓
1.1 + 1.2        drift por SHA, com teste, NÃO bloqueante na 1ª semana
       ↓
2.1              atrito quase nulo hoje
       ↓
2.3              checkbox — o formato de maior adesão
       ↓
2.4 / 2.5        aviso por 2 semanas, depois bloqueio
       ↓
0.1              por último, depois de remover o path filter
```

**Cortado da v1: o item 0.2** (baixar o limiar 180→30 dias). Geraria 22 avisos por
PR sem nenhuma ação associada — que é precisamente como o limiar de 180 virou
decoração. Aviso sem ação é ruído, e ruído treina a ignorar o gate.

---

## Fase A — Limpar antes de trancar

### A.1 · Reconciliar o árbitro `ACHADOS_REAIS.md`

39 issues fechadas citadas como abertas em 66 lugares; **30 no árbitro**. Sem
isto, todo gate downstream nasce sobre dado sujo.

Complicador medido: o árbitro **discorda da auditoria-mãe na severidade de 27 dos
61 achados**, e a nota de reclassificação erra a origem. Reconciliar exige decidir
qual das duas vale — e registrar a decisão.

```bash
# verificar:
python v2/backend/scripts/check_issue_drift.py --root v2/docs/audits   # espera 0
# testar:
pytest apps/core/tests/test_check_issue_drift.py -q
```

- [ ] feito · 30 linhas · 27 severidades divergentes

### A.2 · Correções de dano alto

| # | Alvo | O quê | Rastreado no git? |
|---|---|---|---|
| A.2.1 | `ADR-002` §Consequences | «aprovação NÃO revalida conflitos» — **único achado acionável**: leva a apagar guard que sustenta produção | ✅ |
| A.2.2 | 5 docs de DR | `⛔ restore quebrado (#1611)` — corrigido em `8f392636` | ✅ |
| A.2.3 | `RUNBOOK.md` | `aprender_v2` → `aprender_dev`; sem isso **nenhum** comando roda | ✅ |
| A.2.4 | `.claude/`, `AGENTS.md` | deploy revogado, incl. hook que injeta em toda sessão | ❌ **gitignored** — ver D3 |

```bash
# verificar:
grep -c "aprender_v2" v2/docs/RUNBOOK.md          # espera 0
grep -rlc "#1611" v2/docs/*.md docs/operations/*.md
```

- [ ] A.2.1 · [ ] A.2.2 · [ ] A.2.3 · [ ] A.2.4 (bloqueado por D3)

---

## Fase B — Medir o drift corretamente

### B.1 · Âncora em commit, não em data

**Por quê.** `--since=<data>` é não-determinístico (approxidate usa a hora atual)
e inclui o mesmo dia, acusando a spec corrigida no próprio PR. **O projeto já
inventou a solução certa**: `ACHADOS_REAIS.md` ancora em SHA
(`audit_baseline: 90f6a048`).

**Ação.** Frontmatter de spec ganha `verified_at_commit: <sha>` ao lado de
`last_verified`. O drift passa a ser `git log <sha>..HEAD -- <paths>` — que não
tem hora, não tem fuso e não tem ambiguidade de mesmo dia.

**Pré-requisito técnico** que a v1 ignorou: `check_doc_frontmatter.py` **não sabe
ler a lista** de `sources_of_truth` — a regex `^([A-Za-z_]+):\s*(.*)$` casa a
chave com valor vazio e descarta os itens `  - path`. O parser precisa ser
reescrito antes de qualquer coisa.

```bash
# testar (TDD — escrever antes):
pytest apps/core/tests/test_doc_drift.py -q
# em especial:
pytest apps/core/tests/test_doc_drift.py::test_commit_no_mesmo_dia_nao_acusa -q
pytest apps/core/tests/test_doc_drift.py::test_roda_igual_as_08h_e_as_20h -q
```

- [x] feito — `verified_at_commit` lido pelo parser novo; sem âncora declarada,
  âncora **inferida** do último commit da spec, sempre rotulada como tal.
  17 testes em `apps/core/tests/test_doc_drift.py`.

### B.2 · O gate morre em repositório raso

**Por quê.** `docs-quality.yml:36` faz checkout **sem `fetch-depth`** — profundidade
1. Qualquer `git log` ali vê um commit e reporta «sem drift». O gate ficaria verde
**por falta de dado** — exatamente o diagnóstico deste plano, reproduzido.
Oito outros workflows do repo já usam `fetch-depth: 0`.

**Ação.** Cinto e suspensório: `fetch-depth: 0` no workflow **e** o script aborta
com exit≠0 se `git rev-parse --is-shallow-repository` for `true`. A config some
num refactor; o guard no script, não.

```bash
# verificar:
grep -A3 'actions/checkout' .github/workflows/docs-quality.yml | grep -q 'fetch-depth: 0'
git clone --depth 1 . /tmp/raso && (cd /tmp/raso && python ... ; test $? -ne 0)
```

- [x] feito — `fetch-depth: 0` (PR #1853) + guard no script.
  `test_repositorio_raso_aborta` clona com `--depth 1` e exige exit ≠ 0.

### B.3 · Camada 1 é **relatório**, não bloqueio

**Por quê — a correção de arquitetura da v2.** 21 de 21 specs estão em drift, e
95% das baselinadas recebem commit novo em 7 dias. Um gate que bloqueia sobre
«drift existe» bloqueia sempre, e é revertido na primeira semana.

Drift em repouso é **métrica**, não portão. O portão é por PR (Fase C), que é
limitado ao que aquele PR tocou.

**Ação.** O check roda em todo PR e escreve no **job summary** do GitHub Actions:
specs em drift, quantos commits atrás, delta desde o PR anterior. Nunca falha.

```bash
# verificar:
python v2/backend/scripts/doc_drift_report.py --format=gh-summary
```

- [x] feito · linha de base medida: **21 em drift, 4 sem drift, 6 não medível**
  (31 docs SDD). Sai no job summary; a única saída ≠ 0 é repositório raso.

### B.4 · Detectar `sources_of_truth` encolhendo

**Por quê — o incentivo perverso que a v1 criava.** As 21 specs que declaram
`sources_of_truth` estão 21/21 em drift; as 5 verdes são as 5 que não declaram
nada. **A saída barata é apagar linhas do `sources_of_truth`**, e a v1 premiava
isso.

**Ação.** O check compara a lista contra a versão anterior do arquivo
(`git show HEAD~1:<spec>`). Lista que encolhe exige justificativa no corpo do PR.

```bash
# testar:
pytest apps/core/tests/test_doc_drift.py::test_sot_encolhendo_reprova -q
```

- [x] feito — detector 3 do `check_doc_impact.py`, reaproveitando o waiver.
  6 casos, incluindo os que **não** podem bloquear: crescer, reordenar, spec nova.

---

## Fase C — Fechar o loop, por PR

### C.1 · Índice reverso

Se o PR toca arquivo declarado no `sources_of_truth` de uma spec, aquela spec
ficou suspeita **por construção** — é a definição que a própria spec faz de si.

**Viabilidade remedida em 25/08** (a v1 errou os três números):

| | v1 dizia | real |
|---|---|---|
| Commits sem disparo | 28% | **40%** |
| Média entre os que disparam | 2,4 | **2,6** |
| Caminhos que são diretório | 0 | **1** (`v2/frontend/src/pages`) |

Hubs reais (>4 specs): `rbac/policies.py`=8, `core/urls.py`=7,
`docker-compose.prod.yml`=5. Estes geram **aviso agregado**, não bloqueio.

Por spec atingida, o PR precisa de **uma** de três: alterar a spec, renovar o
`verified_at_commit`, ou declarar `spec-nao-afetada: <arquivo>` com justificativa.

> A terceira saída é deliberada — sem ela o gate vira imposto e é contornado.
> **Mas contorno que ninguém audita vira o caminho padrão em duas semanas**, então
> ela é inseparável do item E.2.

- [ ] feito

### C.2 · Achado ↔ árbitro (`Mxx-yy`)

> [!warning] Verde por vacuidade — medido
> As citações `Mxx-yy` caíram de **11/dia para zero em 21/08**, quando a frente de
> trabalho virou frontend. Este gate protege um caso que hoje ocorre **zero vez
> por semana**. E a faixa que tem o hábito é **feature** (7 de 22 commits tocam
> `.md`), não **fix** (0 de 26).
>
> Vale implementar — é barato e a frente volta para backend. Mas **não conta como
> proteção ativa** e não deve dar sensação de resolvido.

- [ ] feito

### C.3 · Checkbox no corpo do PR — *o formato de maior adesão*

**Por quê.** O `pull_request_template.md` tem 13 checkboxes e **a palavra «doc»
não aparece uma vez**. E o único checkbox verificado por máquina no projeto tem
**100% de adesão em 25 de 25 PRs, com o gate fora do ruleset**.

**Ação.** Item de documentação no template, verificado como o
`staging-gate-audit.yml` faz — que é hoje o único workflow que lê
`pull_request.body`.

- [ ] feito

### C.4 · Módulo novo sem spec — aviso

**Por quê.** **48% do código de produção não tem spec nenhuma** — 175 de 364
arquivos. Todo o valor das fases B e C se aplica só aos outros 189. O gate é cego
para metade do sistema.

Aviso, não bloqueio: exigir spec no mesmo PR da primeira linha se contorna
criando arquivo vazio.

- [ ] feito · cobertura atual: **189/364 (52%)**

---

## Fase D — Testes dos próprios gates

**Bloqueante da v1: zero testes.** Todo `verificar:` era smoke — provava que o
script roda, nunca que reprova.

**Precedente a copiar**, medido: `test_rbac_lint.py` — 7 testes, `subprocess.run`
sobre o script, `tmp_path` para fixtures sintéticas, assert em `returncode`.
Script mora em `v2/backend/scripts/`, teste em `apps/core/tests/`.

> Opção descartada: **management command não serve** para os checks de drift. O
> container não tem o binário `git`, não monta `.git`, e não vê `v2/docs/` nem
> `scripts/` — o volume é `../backend:/app`.

Cada gate precisa, no mínimo:

- [ ] caso **baseline limpo passa** (senão o gate nasce vermelho e é desligado)
- [ ] caso **drift reprova** — a prova de que morde
- [ ] borda: spec sem `sources_of_truth`
- [ ] borda: caminho inexistente · caminho que é diretório
- [ ] borda: `verified_at_commit` malformado ou ausente
- [ ] borda: arquivo renomeado (`git log --follow` aceita **um** pathspec só — por arquivo, nunca em lote)
- [ ] borda: repositório raso
- [ ] borda: fronteira de hora do dia (o bug de approxidate)

---

## Fase E — Observabilidade

### E.1 · Onde a métrica mora

**Por quê o cron está descartado.** A única telemetria do repo,
`ci-runtime-telemetry`, falhou **26 execuções consecutivas** desde 31/07 e
ninguém viu — é `schedule`-only, então não aparece em PR nenhum. Métrica de doc
num cron teria o mesmo fim.

**Ação.** Job summary do PR (item B.3). Aparece onde a pessoa já olha.

- [ ] feito

### E.2 · Auditar o uso do contorno

O `spec-nao-afetada` de C.1 é necessário e é o ponto de erosão. Contagem de uso
por PR entra no mesmo summary. **Se subir de forma sustentada, o gate está
errado — não a pessoa.**

- [ ] feito

### E.3 · Gate que verifica quais gates são gates

**9 de 19 jobs `[required]` não estão no ruleset** — incluindo o que este plano
manda copiar. Check que compara os `name:` dos workflows com os contexts do
ruleset e reporta a divergência.

- [x] feito · **9 de 19** confirmado por parse YAML dos workflows contra
  `GET /repos/:owner/:repo/rules/branches/main` (legível sem admin).
  `check_required_checks.py` + 9 testes. Calibragem oposta nas duas divergências,
  pelo critério de **quem consegue consertar**: context exigido sem job que o
  produza **bloqueia** (trava merge para sempre, conserta-se dentro do PR, hoje
  zero); rótulo `[required]` sem o ruleset exigir apenas **avisa** (é ação de
  admin no ruleset — bloquear PR por algo que o autor não pode consertar desliga
  o gate). Conjunto exigido vazio é lido como falha de medida, não aprovação.

  Os rótulos falsos não são jobs quaisquer: `backend rbac-lint`,
  `backend typecheck (pyright)`, `backend tests (runner)` e `docker parity`
  **não travam merge nenhum** hoje.

---

## Fase F — Consistência doc-a-doc

Classe inteira que a v1 ignorava: doc que contradiz **outra doc**, sem que nenhuma
esteja errada sobre o código.

- [ ] **F.1 · Colisão de identificador.** Dois `ADR-012` diferentes — e **`ADR-019`
      recriou a colisão 21 dias depois de a primeira ser documentada**. Não existe
      registro de numeração. São **três** listas `RF01..RF08` incompatíveis, não
      duas, e a nota que avisa da colisão só conhece uma delas.
- [ ] **F.2 · 35 documentos vivos inalcançáveis** por qualquer índice — inclusive
      uma **terceira** árvore (`specs/`) declarada «leitura obrigatória».
- [ ] **F.3 · `mkdocs --strict` não valida âncora nem cobertura de nav**: 9 âncoras
      quebradas e 21 páginas fora da navegação passam verdes. Falta a chave
      `validation` no `mkdocs.yml`.
- [ ] **F.4 · O índice manda ler o documento que a spec canônica declara obsoleto**
      (`INDEX_DOCUMENTACAO` → `IMPLEMENTACAO_PA`).
- [ ] **F.5 · Referência por caminho em crase não é link** — 11 arquivos SEC ficaram
      inalcançáveis com o checker verde.
- [x] **F.6 · A camada de instrução ficou versionada sem gate de drift.** O D3
      trouxe `.claude/` e `.agents/` para o git, mas versionar não é vigiar:
      `check_agent_instructions.py` só olhava caminho de máquina e credencial, e
      `check_doc_impact.py` nem enxerga a árvore (`RAIZES_DOC` não inclui
      `.claude`). **170 arquivos de instrução citam caminho de código real.**
      Medido: `apps/core/models.py` foi apagado em `4ae989fe` (#213, há 9 meses),
      `views.py` em `733e3933` e `serializers.py` em `18eb7148` — e a instrução
      ainda mandava o agente procurar a regra PA-01 dentro de `Solicitacao.save()`,
      método que não existe.

      **Detector 3 do `check_agent_instructions.py`: citação a caminho apagado.**
      O discriminador é o git (`--diff-filter=D`), não heurística de texto — varrer
      «caminho que não existe» dá 17% de precisão, e filtro por palavra não serve
      porque *um texto que nega a mentira contém as mesmas palavras*. Perguntar ao
      git leva a precisão a 83%.

      Limite conhecido, fixado como teste: declaração histórica **correta** sobre
      arquivo realmente apagado é indistinguível de instrução que ficou para trás
      (`src/api.ts`, removido no #1045). Saída: allowlist com motivo escrito.

      11 testes em `apps/core/tests/test_citacao_apagada.py`; allowlist em
      `.claude/citacoes-apagadas-allowlist.txt`, com as 3 entradas temporárias do
      Lote C marcadas para remoção.

---

## Fase G — Achados de engenharia

Não são documentação. Apareceram na auditoria e não têm dono.

| # | Achado | Sev. |
|---|---|---|
| G.1 | **Container de dev montado em outro worktree**: `c/tmp/aprender-wt-onda1/v2/backend → /app`. O comando de verificação do `CLAUDE.md` **valida código alheio** | alto |
| G.2 | `django-db-connection-pool` é o **único pin exclusivo de produção**, está morto, e é o único que **nunca passa por gate de CVE** (`pip-audit` só lê `requirements.txt`) | alto |
| G.3 | **Três eixos de papel sem árbitro**, e dois endpoints divergem por **precedência vs união** — escrita não auditada derruba aprovação | alto |
| G.4 | `GroupClassificacao` é **gravável por API, altera autorização e não é auditada** — na mesma função onde a escrita vizinha é | alto |
| G.5 | Índice GIN revertido por migration automática — e, **como estava escrito, nunca teria funcionado** | médio |
| G.6 | Paginação: 2 endpoints excedem o teto, 8 o ignoram | médio |
| G.7 | 5 ViewSets de opções **sem rota nenhuma**, com testes verdes que só atestam import | médio |

- [ ] G.1 · [ ] G.2 · [ ] G.3 · [ ] G.4 · [ ] G.5 · [ ] G.6 · [ ] G.7

---

## Decisões abertas

Nenhuma é técnica. Nenhuma deve ser decidida por agente.

### D1 · Documento deve carregar estado de defeito?

34 documentos repetem «isto está quebrado» e apodrecem juntos. A alternativa: a
spec descreve o **contrato**, nunca o **estado**, e linka o árbitro. Um arquivo a
manter em vez de 34.

- [ ] decidido — resposta:

### D2 · O graphify

Declarado leitura obrigatória pelo `CLAUDE.md`; ignorado pelo `.gitignore` —
junto com o próprio `CLAUDE.md`. Sete cópias contraditórias, uma de abril sem
carimbo de commit, e um `wiki/index.md` que a instrução manda navegar e não
existe. Versionar e regenerar em CI, ou remover a instrução.

- [ ] decidido — resposta:

### D3 · Os 155 arquivos fora do git

`.claude/` + `AGENTS.md` são gitignored — **zero rastreados**. É onde drift
**desvia um agente** em vez de confundir uma pessoa, e é o que bloqueia o item
A.2.4. Versionar (ao menos as instruções, não os caches), ou aceitar que essa
camada não tem revisão nem gate.

- [ ] decidido — resposta:

### D4 · Documento concluído: versionado ou fora do git?

É possível ignorar. Mas o custo já foi medido três vezes nesta auditoria —
`CLAUDE.md`, `graphify-out/` e `thoughts/` são ignorados, e por isso *«existem
apenas nesta máquina»*. E `.gitignore:419` já declara: *«Keep public docs
versioned»*.

`_archive/` já atende ao objetivo com 87 arquivos **versionados**, fora da nav do
MkDocs. **Recomendação: manter versionado + gate de isolamento.** Se a decisão for
o contrário, o destino deve ser **fora do repositório** — pasta ignorada dentro
dele parece versionada e não é.

- [ ] decidido — resposta:

---

## Registro de execução

Item sem linha aqui não está feito, independente da caixa.

> Estado: **Fases A, C e B mergeadas.** PR #1847 (D3 + D2), #1853 (Fase A + gate
> de doc viva), e a Fase B em revisão. Fases D–G pendentes; decisões D1 e D4 em
> aberto.
>
> Este bloco dizia «em working tree, não commitado — 166 arquivos» até 25/08,
> quando dois PRs já haviam mergeado. Um plano que mente sobre o próprio estado é
> o defeito que ele descreve, então fica registrado: **o gate da Fase C não pega
> este caso** — ele liga *issue resolvida* a *doc que a cita*, e nenhum dos dois
> PRs citava issue. Lacuna real, candidata à Fase F.

| Data | Item | Comando de verificação | Saída |
|---|---|---|---|
| 25/08 | **D3** · sanitização | `check_agent_instructions.py --tracked-only .claude .agents AGENTS.md CLAUDE.md` | `OK 161 arquivos, nenhum caminho de maquina nem credencial` · exit 0 |
| 25/08 | **D3** · hook intacto | `echo '{"tool_input":{"command":"git push origin main"}}' \| py -3 .claude/hooks/guardrails.py` | exit **2** — CP-07 continua bloqueando |
| 25/08 | **D3** · comando inocente | idem com `git status` | exit **0** |
| 25/08 | **D2** · graphify | `cat CLAUDE.md` | instrução obrigatória removida; ferramenta mantida sob demanda, com o registro do porquê |
| 25/08 | **gate** · morde? | 9 casos negativos via `tmp_path` | 9/9 corretos (ver abaixo) |

### O que foi feito, em detalhe

**D3 — camada de instrução de agente versionada.**

- **10 caminhos absolutos** em `.claude/settings.json` → `$CLAUDE_PROJECT_DIR`
- **1 credencial** (`postgresql://aprender:aprender@…`) → placeholder
  `<usuario>:<senha>`; o valor real vive em `settings.local.json`, que segue fora
  do git — é exatamente o padrão que o Claude Code prevê (local sobrepõe)
- **1 caminho de máquina** em `context-injector.py:27` → derivado do caminho do
  repo, funciona em qualquer clone
- `.gitignore`: liberação **seletiva** — entram instruções, ficam de fora
  `worktrees/` (2001 arquivos), `settings.local.json`, caches e `_archive/`
- **162 arquivos** passam a ser versionados

**Contradição registrada, não escondida.** O ADR-017 decidiu manter `.claude/`
local-only, com a premissa *«nenhum comportamento crítico depende de `.claude/`
num clone limpo»*. **A auditoria falsificou a premissa**: o enforcement da CP-07
vive em `.claude/hooks/guardrails.py`, e a `clausulas-petreas.spec.md` o cita
como o mecanismo. A justificativa está no `.gitignore`, no ponto da mudança.

> Pendente: isto merece emenda ao ADR-017 ou ADR novo. Mudar a decisão sem
> registrar no lugar canônico é o mesmo drift que este plano combate.

**Gate de durabilidade** — `v2/backend/scripts/check_agent_instructions.py`.
Sem ele a sanitização se perde no primeiro `settings.json` colado de volta.

Testes em `apps/core/tests/test_check_agent_instructions.py`, seguindo o
precedente do `test_rbac_lint.py` (subprocess + `tmp_path`). **Comportamento
verificado, 9/9:**

| caso | esperado | obtido |
|---|---|---|
| baseline limpo | 0 | ✅ 0 |
| caminho Windows · Linux · macOS | 1 | ✅ 1 · 1 · 1 |
| credencial em DSN | 1 | ✅ 1 |
| token GitHub PAT | 1 | ✅ 1 |
| `$CLAUDE_PROJECT_DIR` aceito | 0 | ✅ 0 |
| placeholder aceito | 0 | ✅ 0 |
| cache/binário ignorado | 0 | ✅ 0 |

**Defeito encontrado no próprio gate durante o teste.** A primeira versão varria
o diretório inteiro e acusou **28 achados**, dos quais 27 em
`settings.local.json` — arquivo deliberadamente fora do git. Um gate que reclama
do que não está versionado é desligado na primeira semana. Corrigido com
`--tracked-only`, que restringe ao que o `git ls-files` devolve. **28 → 0.**

### Não verificado

- **Expansão de `$CLAUDE_PROJECT_DIR` pelo Claude Code em comando de hook.** Os
  scripts foram invocados diretamente e funcionam; a expansão da variável pelo
  harness não foi exercitada. **Rodar uma sessão no repo e confirmar que os hooks
  disparam antes de commitar.** Backup em `/tmp/settings.json.bak`.
- Os testes pytest não foram executados: `conftest.py` tem fixtures `autouse` que
  exigem Postgres, e o CP-01 manda rodar em Docker. O comportamento foi
  verificado invocando o script com os mesmos casos.
