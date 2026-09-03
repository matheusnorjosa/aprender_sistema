---
title: Espelho Sistema × Planilha
status: living
last_verified: 2026-09-03
owner: backend
sources_of_truth:
  - v2/backend/apps/core/models/organizacao.py
  - v2/backend/apps/core/models/dat_coordenador.py
  - v2/backend/apps/core/views_solicitacao.py
  - v2/backend/apps/core/services/gcal/sync.py
  - v2/backend/apps/core/services/export_contract_importer.py
  - v2/backend/apps/core/rbac/policies.py
---

# Espelho Sistema × Planilha

> **Base de construção do lado-sistema.** Tudo que for construído no `aprender_sistema`
> a partir dos dados das planilhas se apoia neste documento e na **`REFERENCIA-DOMINIO.md`**
> (mantida do lado do `sheets.banco`, snapshot `v14`, `2026-08-21`).

## 0. Regra de governança — quem manda sobre o quê

Dois documentos, duas autoridades, e a fronteira é dura:

- A **`REFERENCIA-DOMINIO.md`** é autoridade sobre **o que a planilha contém e o que significa**.
- **Este documento** é autoridade sobre **o que o sistema faz**.
- Cada um **cita** o outro; **nenhum conclui sobre o outro.**

Três regras que saíram de um erro real (uma auditoria de um lado sobre o código do
outro que trouxe 5 achados falsos, §3):

1. **Afirmação sobre o código do outro lado não entra em documento de referência sem
   reprodução `arquivo:linha`.**
2. **Para provar que algo é "morto", é preciso alcançar as formas de estar vivo** —
   chamada por método, endpoint de import, query em runtime, admin, invariante de teste,
   contrato público. "Zero ocorrências do nome" ≠ "zero uso".
3. **Achado já refutado não volta.** Por isso os refutados ficam **escritos** (§3).

Rótulos, como na `REFERENCIA-DOMINIO.md`: **MEDIDO** (contado no código/banco, com
`arquivo:linha` ou query), **DECIDIDO** (escolha do dono — não relitigar), **ABERTO**
(sem dono ainda), **DEFEITO** (erro conhecido com fila).

---

## 1. O modelo de domínio do SISTEMA (verificado)

### 1.1 Hierarquia de produto

**MEDIDO** (`models/organizacao.py`, FKs): `ProjetoGeral` → `Projeto` → `Coleção` → `Produto`.

- `Projeto.projeto_geral` → `ProjetoGeral` (família); `Projeto.gerencia` → `Gerencia` (o setor).
- `Colecao.projeto` → `Projeto`; `Produto.projeto` + `Produto.colecao`.
- `Produto` carrega o tipo (Aluno/Professor) que alimenta o cálculo de códigos do DAT.

> ⚠️ **Alinhamento com a `REFERENCIA-DOMINIO.md`:** do lado da planilha, `Coleção`
> **não é** nível da hierarquia (`produto.colecao` vazio 784/784) e significa **edição
> anual do material**. No sistema, `Colecao` é um model **vivo** (endpoint de import +
> FK `Produto.colecao` + leitura no dashboard DAT, §3), mas hoje sem dado. Não construir
> regra de negócio sobre `Colecao` até o significado "edição anual" estar modelado.

### 1.2 Identidade das pessoas — três camadas independentes

- **Setor** — grupo Django (13, `apps.core.constants.SETOR_GROUPS`).
- **Função** — grupo Django (5: Formador, Coordenador, Apoio de Coordenação, Gerente,
  Assistente Administrativo).
- **Vínculo** — `EquipeGerencia(usuario, gerencia, papel, valid_from/to)`; vigência via
  `EquipeGerencia.vigentes_em()` (`models/organizacao.py`, é o SSOT de vigência, RD-06).

**MEDIDO:** `EquipeGerencia.PAPEL_CHOICES` = `GERENTE, COORDENADOR, APOIO, FORMADOR`
(`models/organizacao.py:247-252`). Escopo de autorização deve sair do **vínculo**
(`EquipeGerencia` + setor canônico), não do **grupo** — grupo serve para *capability*,
vínculo serve para *escopo*.

### 1.3 Fluxo de aprovação

**MEDIDO:** `Projeto.fluxo ∈ {SUPER, NAO_SUPER}`. Deriva do **setor** (não da aba da
planilha). SUPER → pendente de aprovação (PA-01..07); NAO_SUPER → auto-aprova. Ver
[`politica-aprovacao.spec.md`](./specs/domain/politica-aprovacao.spec.md).

### 1.4 Solicitação → participantes → Google Agenda

`Solicitacao(projeto, municipio, ...)` → `Participation` (papéis `COORDENADOR`,
`FORMADOR`, `COORD_ACOMPANHA`, `CONVIDADO`) → aprovação → publicação no GCal.
Contrato em [`solicitacao-approval.spec.md`](./specs/backend/solicitacao-approval.spec.md).

### 1.5 DAT, Planos e Disponibilidade

- **DAT** transforma compra em acesso funcionando (trilhas FORMAR/AVALIAR). Ver
  [`dat.spec.md`](./specs/backend/dat.spec.md).
- **Plano** `PlanoFormacoes(municipio, projeto, coordenadores→Usuario M2M)` → `Formacao` →
  `Acompanhamento`/`Prova`.
- **Disponibilidade** cruza `AvailabilityBlock` + `Deslocamento` (RD-01..08). Ver
  [`availability.spec.md`](./specs/backend/availability.spec.md).

---

## 2. Estado de prontidão para o import — as dependências duras

O import (via `views_import_*` + `export_contract_importer`, [`imports.spec.md`](./specs/backend/imports.spec.md))
**recebe arquivo, não raspa**. Mas o sistema tem lacunas que precisam de **migration antes**
do import real:

| MEDIDO no banco (2026-08-26) | Estado | Consequência |
|---|---|---|
| `Projeto.gerencia` (setor) | **NULL em 124/125** | sem setor, o gate D6 não roda |
| `Projeto.projeto_geral` (família) | **NULL em 125/125** | a regra de códigos mora na família → **nenhum** cálculo funciona |
| `Gerencia.setor_canonico` | **campo não existe** | o de-para do sheets.banco (v15) não tem onde pousar |
| `papel` SUPORTE/OPERACIONAL | **não existem no enum** (só APOIO) | 9 vínculos DAT sem casa (§4) |
| `desativado_localmente` | **campo não existe** | o import reativaria quem foi desligado (§4) |
| SKU cadastrado como projeto | resíduo ETL | diferença 125 (sistema) × 114 (planilha) |

> **Nada disso é re-derivável no Django.** DECIDIDO (dono, 25/08): os scripts de raspagem
> estão aposentados — **importar, não re-derivar**. A associação projeto↔setor vem do
> import (contrato v15), não de código.

---

## 3. A §9.1 re-verificada — o que agir e o que NÃO agir

Registro durável da verificação adversarial de 2026-08-26 (11 afirmações de auditoria do
`sheets.banco` sobre este código, re-verificadas com evidência `arquivo:linha`).
**Placar: 1 confirmada · 5 reclassificadas · 5 refutadas.** As refutadas ficam escritas
**para não voltarem** (regra 3, §0).

### 3.1 ✅ CONFIRMADO — agir

- **`_update_formadores` (`views_solicitacao.py`)** não filtrava `is_active` (o create
  filtra em `:378/:384`) e reconciliava só `FORMADOR`, nunca `COORD_ACOMPANHA`.
  **Corrigido no PR #1886** (filtra ativos + reconcilia os dois papéis; guests por
  e-mail seguem só no create — D6c em revisão pelo dono).

### 3.2 🟡 RECLASSIFICADO — o núcleo sobrevive, refatorar (não apagar)

| item | verdade que sobra | o que a auditoria errou |
|---|---|---|
| **`DATCoordenador`** | cadastro paralelo: 12 campos de conteúdo, **sem FK de identidade** para `Usuario`. Refatorar p/ `(usuario_fk, area)` resolvendo por CPF (épico #1833) | "o importer preenche todos" — **falso**; grava 4 (`export_contract_importer.py:838-844`) |
| `AcaoDAT` | endpoint `/dat/acoes/` é candidato a deprecação (nenhuma tela React lê) | comentário "LEGACY" está **certo**; o model **é escrito** pelo import (`dat_cadastros_import.py:337`); são 2 serializers, não 1 |
| `DATCompra` | só `valor_unitario`/`qtd_utilizada` são digitação manual | `quantidade` **é importada e load-bearing** no cálculo de códigos. Manter |
| `DATFormacao` | só "sem importador em lote" | 29 campos (não 24); CRUD vivo; domínio distinto. Manter |
| pares status/data (`dat_registro.py`) | **manter os 7** | conflacionou `DATRegistro` (emite 7) com `DATCadastro` (4 colunas) |

### 3.3 🔴 REFUTADO — NÃO AGIR

| afirmação | por que caiu (evidência) |
|---|---|
| "~20 classes RBAC mortas" | **load-bearing.** `test_rbac_policies.py:119 test_every_matrix_key_has_policy_class` obriga uma classe `Can*` por key de `ACCESS_POLICIES`; `GET /api/me/policies/` (`views/me.py:11-12`, `urls.py:165`) é **contrato público do frontend**. Apagar quebra o teste **e** o contrato |
| "`RegistroConclusaoAcao`/`RegistroAncora` mortos" | **vivos** — persistência de dois endpoints; a view chama o **método** do model (`.registrar_ancora()`, `.concluir()`), não o nome da classe |
| "`Colecao` nunca exposto" | **vivo** — `POST /api/colecoes/import/` + FK `Produto.colecao` + dashboard DAT |
| "`FeriadoLocal` nunca usado" | **vivo** — query em runtime (`business_calendar_service.py:97`), admin, Celery de notificações |
| "varrer os 6 scripts atrás de de-para hardcoded antes de apagar" | **não há** `SETOR_DO_PROJETO`; o único alias (`IDEB`→Gestão Escolar) já vive em `resolvers.py:314-319`. Os 6 scripts são **seguros de remover** |

---

## 4. Requisitos que saem dos relays (do lado-sistema)

### 4.1 Desativação local resiste à fonte — **requisito duro do import**

**DECIDIDO (dono, 25/08):** a planilha **não será corrigida**. Pessoa desligada (ex.:
Elienai) permanece na aba `ATIVOS` → o `usuario.csv` a emite ativa → o import a criaria/
manteria ativa.

> **Regra:** **o import não pode reativar quem foi desativado no sistema.** Precisa de um
> conceito de **estado local que a fonte não sobrescreve** — campo `desativado_localmente`
> (ou lista de exceção) que vence o valor importado. **Reativar é decisão humana, não
> efeito de sync.** Quando a pessoa some da fonte: **desativar, nunca apagar** (o histórico
> de quem conduziu formação é registro).

O PR #1886 (`is_active` no update) é o **primeiro degrau**; `desativado_localmente` é o
segundo (garante que a desativação cola entre syncs).

### 4.2 Troca de coordenador em lote — **evento de negócio**, não edição em massa

**Requisito (dono):** trocar coordenador em lote para casos como o do Elienai. **Não** é
"substituir A por B" — substituição cega reescreveria o histórico (o Elienai **conduziu**
63 formações passadas). É **transferência de carteira com data de corte**:

1. **antes do corte** — fica como está (registro do que aconteceu);
2. **do corte em diante** — passa ao sucessor;
3. **reconciliar os eventos já publicados** — ver §5.

Granularidade por pessoa (opcionalmente filtrada por projeto/setor); trilha de **quem
transferiu, quando, e qual a data de corte**. É recorrente. **Planejar antes de
implementar (CP-04)** — depende do import (precisa do dado).

### 4.3 Co-titularidade de plano — modelar para **N** — ✅ FEITO (2026-09-03)

**DECIDIDO (dono, 25/08)** e **IMPLEMENTADO:** dois coordenadores respondem **igualmente** por um par
município×projeto (`VIDA E MATEMÁTICA`, `UNIÃO DOS PALMARES`), caso recorrente. `PlanoFormacoes.coordenador`
(FK única) virou `coordenadores` (**M2M**, #1958 + reconcile #1960): a chave natural `(municipio, projeto, ano)`
segue identificando **1 plano** — não se parte o cronograma. A medição do sheets.banco (RELAY 32/34) confirmou
**co-liderança da mesma formação** (não turmas separadas) e que pôr o coordenador na chave inflaria a CH do
município. Golden: **32 planos co-liderados** (display "A & B"); deployado em prod `v2026.09.03-f9521ba`.
Dados de co-coordenação em prod = re-import futuro à parte.

### 4.4 Papel SUPORTE/OPERACIONAL

**DECIDIDO (dono):** SUPORTE e OPERACIONAL são cargos do **DAT** (não coordenação) →
**não** mapeiam para `APOIO`. `APOIO DE COORDENAÇÃO` tem as **mesmas permissões de
COORDENADOR**. As pessoas de SUPORTE/OPERACIONAL veem a grade via a capability do grupo
DAT (`view_all_availability`), não via papel.

---

## 5. GCal — a resposta que decide a viabilidade da §4.2

**Pergunta (sheets.banco):** re-publicar um evento já no Google Agenda **atualiza** ou
**duplica**?

**MEDIDO — ATUALIZA, não duplica.** O `eventId` é **determinístico por Solicitação**
(`services/gcal/validation.py:59 _event_id_for` → `{PREFIX}-{id}`), e o sync decide
(`services/gcal/sync.py:157-161`): aprovado + evento existe (ou adota) → **UPDATE**;
não existe → CREATE; não-aprovado com id → DELETE.

**Consequência:** a parte 3 da transferência (§4.2) é **viável com a máquina que já
existe** — se a troca editar os participantes da **mesma** solicitação (mesmo id) e
re-sincronizar, o convite é **atualizado** (attendees passam ao sucessor), sem duplicar.
Não é preciso passo manual. ⚠️ Só vale editando as solicitações existentes; **criar novas**
solicitações criaria eventos novos.

---

## 6. O de-para de setor no sistema

O predicado do gate D6 recomendado pelo sheets.banco compara **setor canônico** dos dois
lados (não igualdade de gerência — igualdade barraria 46% da operação). No sistema isso
exige:

1. `Gerencia.setor_canonico` (campo novo, migration) — recebe o de-para que o sheets.banco
   emite na v15;
2. o setor do `Projeto` populado via import (`projeto.gerencia`, hoje 124/125 vazio);
3. o predicado `EquipeGerencia.vigentes_em().filter(usuario=user, gerencia__setor_canonico=<setor do projeto>)`.

Enquanto (1) e (2) não existem, **o gate D6 fica bloqueado** — é dependência de import,
não de código de autorização.

---

## 7. Sequenciamento e estado

| # | tarefa | estado |
|---|---|---|
| 1 | `_update_formadores` (`is_active` + COORD_ACOMPANHA) | ✅ **PR #1886** (gate 8/8) |
| 2 | remover os 6 scripts de raspagem | pronto (§3.3: seguro) |
| 3 | migrations: `setor_canonico`, `projeto_geral`, papel, `desativado_localmente` | **depois da v15** |
| 4 | import real (dry-run → apply, autorização) | depois de 3 |
| 5 | gates D6/D7 + cálculo de códigos | depois de 4 |
| 6 | feature de transferência de carteira (§4.2) | planejar (CP-04), depois de 4 |

> **Regra imutável (RF01):** NÃO importar dado real até um dry-run do `--apply` passar verde
> + autorização. O caminho crítico do import é a **v15** do `sheets.banco`.

---

## 8. Decisões fechadas (relevantes ao sistema) — não relitigar

| data | decisão |
|---|---|
| 21/08 | de-para gerência→setor por projeto; SUPER deriva do setor |
| 25/08 | scripts de raspagem aposentados — importar, não re-derivar |
| 25/08 | SUPORTE/OPERACIONAL não viram APOIO; APOIO = permissões de COORDENADOR |
| 25/08 | coluna B da FORMAÇÕES = governança (coordenador ≠ formador) |
| 25/08 | planilha não será corrigida → desativação tem de ser representável no sistema |
| 25/08 | co-titularidade de plano modelada para N; transferência = evento com data de corte |
