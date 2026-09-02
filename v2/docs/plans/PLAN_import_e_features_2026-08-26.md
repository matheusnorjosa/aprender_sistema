---
title: Plano — Import da planilha + features derivadas
status: draft
last_verified: 2026-09-02
owner: backend
related:
  - ../specs/backend/imports.spec.md
  - ../specs/backend/dat.spec.md
  - ../specs/backend/rbac.spec.md
  - ../specs/domain/politica-aprovacao.spec.md
---

# Plano — Import da planilha → sistema + features derivadas

## ⏩ Status 2026-09-02 — IMPORT REAL FEITO, golden dev = só-v16

`main = 7beb36cc`, 0 PRs. O dono AUTORIZOU o import real (RF01) e pediu "montar tudo localmente pra
testar". **PRs mergeados** (v16.4→lookup): #1943 (solicitacao: `solicitante_cpf/email` + procedência +
filtro `linha_completa` + afrouxa `apoio_requires_supervisor`) · #1944 (participation: guarda
`match_procedencia` vazio→`guest_nome`) · #1945/#1947 (MeEventSerializer.`participantes` + coluna
MeusEventos do Desktop) · #1946 (projeto rótulo `projeto_geral` NULL + guard família-vazia+dat,
Refs #1897) · #1948 (lookup dropdown projeto+município: nome-limpo, esconde kits numerados / hubs
UF-vazia, `include_kits`/`include_hubs`, teto 200).

**Import real aplicado** (create-only, backup antes) da fatia appliable → golden só-v16: Solicitacao
**3.085** · Participation **12.093** · DATCompra **2.214** · DATRegistro/Cadastro/Acao · PlanoFormacoes
**380** · Municipio ativos **108** · Projeto ativos **116**. Depois: **purga do legado**
(`created_at<hoje` — o golden tinha snapshot de maio misturado) + **limpeza de catálogo** (projeto:
kits/dups/cruft; município: dup-acento/truncado/geo-errado + **cruzamento IBGE 5.571**). Regra do dono:
**IBGE é SINAL, não exclusão** (AMIGOS DO BEM/APRENDER são necessidade operacional).

**Falta a última fatia** (o "todos os dados"): **5 handlers NOT_IMPLEMENTED** no importer — `formacao`
(1.229) · `acompanhamento` (111) · `prova` (51) · `availability_block` (53) · `deslocamento` (1.505).
No golden só-v16 essas telas ficam vazias até serem codadas (TDD, poucos PRs). Também: fonte corrige
**Capivari-PR→SP** (#129, typo real) → re-import; mesclar `Miudezas`(forma curta)→`PROJETO MIUDEZAS E
DESCOBERTAS`. Playbook + aprendizados: memória `reference-golden-datafix-and-ibge-cleanup-2026-09-02`,
`feedback-gunicorn-dev-sighup-reload`, `feedback-ibge-municipio-validation-signal`,
`feedback-multi-claude-relay-verify-system-side` (RELAY 60/63: correção bidirecional, DictReader≠posição).

## Contexto (por quê)

O `aprender_sistema` vai substituir as planilhas. O dado limpo (pessoas, projetos,
setores, vínculos, compras, eventos) já existe do lado do `sheets.banco` (contrato v14,
snapshot 2026-08-21) e entra por **import** — não por raspagem (os scripts de raspagem
estão aposentados, DECIDIDO 25/08). Este plano cobre tudo que o **lado-sistema** precisa
fazer para consumir esse contrato e as features que saem dele.

**Objetivo de dev (a régua de "pronto").** O ambiente de dev é o **ponto de validação**: o
sistema inteiro deve funcionar corretamente aqui — as **páginas exibindo os dados certos**,
os fluxos operando — antes de qualquer coisa ir para produção. **Exceção:** a **criação de
eventos no Google Agenda não precisa funcionar em dev** (já funciona em prod; dev usa o GCal
*fake client*). Ou seja, o import + os data-fixes (ex.: as duplicatas de projeto) + os gates
não existem só para pôr dado no banco — existem para deixar dev **correto e navegável**. Cada
onda com impacto de dado fecha com uma checagem de **página/tela**, não só de linha de tabela.

Autoridade e detalhe: `ESPELHO_SISTEMA_PLANILHA.md` (o que o sistema faz, em `v2/docs/`) +
`REFERENCIA-DOMINIO.md` (o que a planilha contém, no `sheets.banco`).

> **Caminho crítico:** a **v15 foi ENTREGUE** (2026-08-27, snapshot 2026-08-21, 32 arquivos, com
> `setor_canonico`, `segmento_norm`, `usuario.status`, correções). As migrations/import de verdade
> podem começar. **RF01 imutável:** não importar dado real até um dry-run do `--apply` passar verde +
> autorização do dono.

## Verificação crosscheck v15 (2026-08-27) — o que o código REALMENTE tem

Rodei um workflow de 8 agentes cruzando cada afirmação do **lado-sistema** da v15 contra o código
(file:line). O relay veio enviesado "mais pronto do que é" (2 claims cravaram, 6 corrigidos):

| claim do relay | veredicto | realidade no código | issue |
|---|---|---|---|
| `projeto.setor` × `gerencia.setor_canonico` (gate D6) | 🔶 reclass | **campos criados** (#1893 ✅ — `get_setor` prefere o model, fallback derivado); falta **popular** via import (#1897); `projeto.gerencia` 124/125 vazio | #1893 ✅ · #1898 |
| `EquipeGerencia.vigentes_em()` + setor | 🟡 parcial | esqueleto **roda em prod**; `Gerencia.setor_canonico` **criado** (#1893 ✅, só em Gerencia) | #1893 ✅ |
| `external_event_id` importável | 🔶 reclass ⚠️ | campo é **cache determinístico** (`asv2-{id}`); **NÃO importável** (landmine `tipo_compra`≠`tipo`) | #1899 |
| Colecao tem import próprio | ✅ ok | `POST /api/colecoes/import/` existe; remover `colecao.csv` é inócuo | — |
| não apagar model `Prova` | ✅ ok | model **vivo** (PATCH `update_prova`, serializers, prefetch); "0 provas" = dado vazio | — |
| `usuario.status`/`desativado_localmente` | 🔴 refutado ⚠️ | **não existem** (só `is_active`); a bomba foi **corrigida** (never-reactivate) e o campo persistente `desativado_localmente` **existe** (#1894) | #1891 ✅ · #1894 ✅ |
| 14 entidades "implementadas" | ✅ ok | `solicitacao`+`participation` ganharam handler classify+apply no **#1935** (`guest_nome`/D1, email-first, papel-por-posição); `equipe_gerencia` #1895; `gerencia` só classifica (by design) | #1895 ✅ · #1896 ✅ |
| `segmento_norm`; projeto_geral→nr_codigos | 🟡 parcial | `segmento_norm` **não é coluna**; nr_codigos usa `DATRegistro.projeto_geral`, **não** `Projeto.projeto_geral` | #1896 #1897 |

**Rastreamento: milestone #22 — Import v15 → dev correto** (issues #1891–#1900). Ordem sugerida:
**#1891 ✅** (bomba usuarios_import — corrigida no #1902) → **#1892** (merge VIDA `--apply` — aplicado no dev) → **#1893 ✅** (campos setor) / **#1894 ✅** (desativado_localmente) →
**#1895/#1896/#1897** (import) → **#1898** (gates D6/D7) → **#1899** (relay external_event_id) → **#1900**
(validação de dev). As duas landmines (external_event_id, bomba de reativação) foram evitadas por verificar
antes de construir.

## Decisões travadas (não relitigar sem o dono)

| # | decisão | fonte |
|---|---|---|
| D6a | participante interno = do **setor** do projeto **E** com a função certa (via setor canônico) | dono 25/08 |
| D6b | projeto sem setor = erro (fail-closed) — mas resolve por import, não deve existir | dono 25/08 |
| D6c | convite por e-mail que casa com interno → em revisão (fenômeno pequeno, 19 pessoas) | aberto |
| D7 | grade mensal só p/ coordenação: `{COORDENADOR, APOIO, GERENTE}` ou `view_all_availability` | dono 25/08 |
| — | `APOIO DE COORDENAÇÃO` = mesmas permissões de `COORDENADOR` | dono |
| — | `SUPORTE`/`OPERACIONAL` = cargos DAT, **não** viram APOIO; grade via cap do grupo DAT | dono 25/08 |
| — | desativação tem de ser representável no sistema (planilha não será corrigida) | dono 25/08 |
| — | o import **não pode reativar** quem foi desativado no sistema | derivado |
| — | co-titularidade de plano modelada para **N** (não 2) | dono 25/08 |
| — | troca de coordenador = **transferência de carteira com data de corte** (evento de negócio), não edição em massa | dono 25/08 |
| — | **dev deve funcionar 100% correto** (páginas + dados) como validação pré-prod; exceção: criação de eventos GCal (já ok em prod) | dono 27/08 |
| — | setor comparado por **setor canônico** (não igualdade de gerência) | sheets.banco (medido: igualdade barra 46%) |

## Ondas (wave-based, CP-04)

### Onda 0 — Baseline (feito / em andamento)

- [x] **#1886** — `_update_formadores` filtra `is_active` + reconcilia `COORD_ACOMPANHA` (MERGED).
- [ ] **#1887** — doc-espelho (autoridade do lado-sistema) — em CI.

### Onda A — Limpeza desbloqueada (NÃO depende da v15)

- [ ] **A.1** Remover os 6 scripts de raspagem (verificados seguros — sem de-para único; alias já
      em `resolvers.py:314-319`): `auditoria_planilhas.py`, `auditoria_planilhas_v2.py`,
      `normalize_to_etl.py`, `seed_projetos_fluxo_from_sheets.py` (+ teste + spec `dev-tools`),
      `validate_etl.py`, `check_data.py`. **Verificação:** `git grep` limpo + suíte verde.
- [ ] **A.2** (opcional) Deprecar o endpoint `/dat/acoes/` de `AcaoDAT` (nenhuma tela lê; escrita
      entra pelo import) — via `deprecation-and-migration`, **sem** apagar o model.

### Onda B — Modelo + migrations (depende da v15)

- [x] **B.1** `Gerencia.setor_canonico` (CharField) ✅ #1893 — recebe o de-para do sheets.banco.
- [x] **B.2** Setor do projeto: **`Projeto.setor` criado** (#1893 ✅ — decisão: campo próprio +
      fallback derivado de `gerencia.nome_setor` no `get_setor`, sem regressão). Falta **popular**
      via import (#1897).
- [ ] **B.3** `projeto.projeto_geral` (hoje 125/125 vazio) — a regra de códigos mora na família.
- [ ] **B.4** Papel `SUPORTE`/`OPERACIONAL` no enum de `EquipeGerencia.papel` (ou mapeamento
      explícito) — sem promover a APOIO.
- [x] **B.5** `Usuario.desativado_localmente` (BooleanField) ✅ #1894 — estado local que o import não
      sobrescreve. Reativar = ação humana.
- [ ] **B.6** Refactor `DATCoordenador` → `usuario_fk` (identidade por CPF), reduzindo os 12 campos
      duplicados a `(usuario_fk, area)` — épico **#1833**. TDD + migração de dados.

### Onda C — Import real (depois de B + v15; RF01)

- [ ] **C.1** Import de `gerencia`/`equipe_gerencia` com `setor_canonico`; mapear papel.
- [ ] **C.2** Import de `projeto` (setor) + `projeto_geral` (regra de códigos).
- [ ] **C.3** Import respeitando `desativado_localmente` (não reativa quem foi desligado localmente).
- [ ] **C.4** Reconcile **125 × 114** — limpar SKU-como-projeto (`TRÂNSITO LEGAL ANOS INICIAIS`/`GUIA`)
      e não-projetos (`Coordenadores`, `Diretores`, `TESTE E2E`, `projeto`).
- [ ] **C.5** Dry-run → apply com allowlist + autorização do dono (RF01). Reconciliar os `__rejeitadas`.

### Onda D — Gates de autorização (depois de C)

- [ ] **D.1** Gate D6 (ator×alvo em participantes): `EquipeGerencia.vigentes_em().filter(usuario,
      gerencia__setor_canonico=<setor do projeto>)`, função casada, fail-closed sem setor. TDD.
- [ ] **D.2** Gate D7 (`HasSectorAccess` ramo `gerencia_id is None`): exigir `papel__in={COORDENADOR,
      APOIO, GERENTE}` além de `vigentes_em()`. TDD. (Runtime → staging gate.)

### Onda E — Cálculo de códigos (depois de projeto_geral importado)

- [ ] **E.1** `nr_codigos` por linha de compra (2 fórmulas: professor×1,1 e aluno÷20;
      `conta_para_codigos`). Plano já rascunhado (`graceful-floating-bunny`). Depende de B.3+C.2.

### Onda F — Features de negócio (depois de C)

- [ ] **F.1** **Transferência de carteira com data de corte** (evento de negócio): preserva o
      passado, passa o corte→frente ao sucessor, re-publica os eventos futuros (GCal **atualiza**
      por eventId determinístico — viável), trilha de quem/quando/corte, granularidade por
      pessoa/projeto/setor. **Planejar via `/create-plan` próprio.**
- [ ] **F.2** Co-titularidade de plano para **N** (`PlanoFormacoes` — hoje FK única). Sem pressa
      (sem caso vivo). Migração para N responsáveis.
- [ ] **F.3** Controle de **compra adicional** (herdar da planilha `⚙️ CONFIG!AT:BG`): compra fora
      do fluxo vira candidata + ciência nomeada + registro de quem/quando. Sem equivalente hoje.

### Onda G — Follow-ups menores

- [ ] **G.1** `nome_curto` (recorte de 2 palavras) armazenado — fallback de casamento por nome.
- [ ] **G.2** `Colecao`: decidir "edição anual do material" (dado real) ou parar de exportar.

### Onda H — Validação de dev (transversal — a régua de "pronto")

Não é uma onda no fim: é a checagem que **fecha cada onda com impacto de dado**. Dev tem de ficar
**correto e navegável** (ver Contexto).

- [ ] **H.1** Após reconcile/merge de projeto: contagem por projeto correta **nas telas** (Compras,
      DAT, Planos, Disponibilidade) — não só na tabela.
- [ ] **H.2** Após o import (C): as páginas de `AppRoutes.tsx` exibem os dados reais sem erro
      (setores, projetos, pessoas, vínculos, compras, eventos).
- [ ] **H.3** Fluxos ponta-a-ponta em dev: criar solicitação → aprovar → grade → planos.
      **Exceção:** a publicação real no Google Agenda **não** é exercida em dev (GCal *fake client*;
      já funciona em prod).

## O que preciso do `sheets.banco` (para desbloquear B/C/E/F)

Ver a lista consolidada em [§ Requests](#requests-ao-sheetsbanco) abaixo.

## Sequenciamento / dependências

```
Onda 0 ✅ ──> Onda A (agora, independente)
                   │
   v15 (sheets.banco) ──> Onda B ──> Onda C ──> Onda D (gates)
                                        │  └────> Onda E (códigos)
                                        └───────> Onda F (features)
                                                  Onda G (follow-ups)

   Onda H (validação de dev) — transversal: fecha CADA onda de dado com
   checagem de página/tela, não só de tabela. Régua de "pronto" pré-prod.
```

## Riscos / o que NÃO fazer

| risco | mitigação |
|---|---|
| import reativa desligado (Elienai) | **corrigido** (#1902/#1891 guarda never-reactivate; #1894 refina: `Usuario.desativado_localmente` distingue desativação local da planilha — import reativa só quem a planilha desativou) |
| comparar setor por igualdade barra 46% | usar `setor_canonico` dos dois lados (B.1) |
| transferência duplica evento no GCal | eventId determinístico → UPDATE; editar solicitação existente, não criar nova |
| import cego sobrescreve data-fix manual | dry-run verde + autorização (RF01); create-only + never-overwrite |
| migration para contrato que ainda muda | migrations (B) só depois da v15 |
| apagar model "morto" que é vivo | seguir a §9.1 re-verificada do espelho (🔴 NÃO AGIR) |

## Requests ao `sheets.banco`

**v15 ENTREGUE** (setor_canonico · projeto_geral 107/117 · segmento_norm · usuario.status das 3 abas ·
prova.csv com log explícito de origem-vazia · colecao.csv removido · 3 projetos de catálogo). Item que
**volta** ao sheets.banco (#1899): **`external_event_id` reclassificar** — o sistema deriva a identidade
(`asv2-{id}`) e não ingere id externo; **não é campo importável**. Conferir se a coluna não é, na verdade,
outra coisa (link/observação).

**Dados/respostas:** lista dos 34 eventos futuros do Elienai (município/data/status publicação) —
p/ desenhar a transferência (F.1) · quem atende os 21 projetos órfãos (A COR DA GENTE, ED
FINANCEIRA, SOU DA PAZ, TRÂNSITO LEGAL) · reconcile 125×114 (mando minha lista, ele aponta os 11) ·
`nome_curto` armazenado no `usuario.csv` · confirmar que não há sinal de desativação na fonte
(Elienai fica em ATIVOS) → 100% gerido localmente.

## Aberto — dono

D6c (convite por e-mail interno) · quem atende os 4 setores órfãos · desenho da parte 3 da
transferência (assume-se re-publicação automática via GCal) · higiene do `usuario.csv` (CPF
duplicado/ausente, mod-11, cadastro sem cargo).
