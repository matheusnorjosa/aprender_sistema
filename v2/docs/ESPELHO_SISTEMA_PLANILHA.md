---
title: Espelho Sistema × Planilha
status: living
last_verified: 2026-10-19
owner: backend
sources_of_truth:
  - v2/backend/apps/core/models/organizacao.py
  - v2/backend/apps/core/models/dat_coordenador.py
  - v2/backend/apps/core/views_solicitacao.py
  - v2/backend/apps/core/services/gcal/sync.py
  - v2/backend/apps/core/services/export_contract_importer.py
  - v2/backend/apps/core/rbac/policies.py
  - v2/backend/apps/core/services/solicitacao_scope.py
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

**MEDIDO** (`models/organizacao.py`, FKs): `ProjetoGeral` → `Projeto` → `Produto`. Na tela, `ProjetoGeral` se chama **Coleção** (decisão do dono, 06/10/2026).

- `Projeto.projeto_geral` → `ProjetoGeral` (família); `Projeto.gerencia` → `Gerencia` (o setor).
- `Produto.projeto` → `Projeto`.
- `Produto` carrega o tipo (Aluno/Professor) que alimenta o cálculo de códigos do DAT.

> ⚠️ **Coleção = família (decisão do dono, P1, 05/10/2026):** coleção é a obra, que no sistema
> é o `ProjetoGeral`. O model `Colecao` e a FK `Produto.colecao` (vazios em produção) saíram na
> migração 0118, com o import `POST /api/colecoes/import/`; os cards "Coleções ativas" e
> "Quantidade por Coleção" do dashboard de compras contam a família do projeto da compra. Do
> lado da planilha, `produto.colecao` já vinha vazio (784/784).

### 1.2 Identidade das pessoas — três camadas independentes

- **Setor** — grupo Django (13, `apps.core.constants.SETOR_GROUPS`).
- **Função** — grupo Django (5: Formador, Coordenador, Apoio de Coordenação, Gerente,
  Assistente Administrativo).
- **Vínculo** — `EquipeGerencia(usuario, gerencia, papel, valid_from/to)`; vigência via
  `EquipeGerencia.vigentes_em()` (`models/organizacao.py`, é o SSOT de vigência, RD-06).

**MEDIDO:** `EquipeGerencia.PAPEL_CHOICES` = `GERENTE, COORDENADOR, APOIO, FORMADOR`, mais `EQUIPE`
("Equipe administrativa", 05/10/2026 — ver §4.4) (`models/organizacao.py`). Escopo de autorização sai do **vínculo**
(`EquipeGerencia` na gerência do projeto desde o PR 9; o setor canônico não dá escopo, §6), não do
**grupo**. Desde o PR 12 (`RBAC_FONTE=lotacao`) a *capability* também vem do vínculo (pacote do
perfil da gerência + direitos do papel); o grupo de Setor/Função é etiqueta.

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
| `Projeto.gerencia` (setor) | **NULL em 124/125** (medição histórica; hoje 0 projetos ativos sem gerência em produção, `ACHADOS_REAIS` M10-04) | sem gerência, o escopo nega (fail-closed, PR 9) |
| `Projeto.projeto_geral` (família) | **NULL em 125/125** | a regra de códigos mora na família → **nenhum** cálculo funciona |
| `Gerencia.setor_canonico` | **existe** (mig 0099), gravado pelo importer | o de-para v15 já pousa; desde o PR 9 o escopo não usa setor (§6) |
| `papel` SUPORTE/OPERACIONAL | **não existem no enum**; o papel `EQUIPE` ("Equipe administrativa") foi criado em 05/10/2026 | os 9 vínculos DAT vão para `EQUIPE` (§4.4) |
| `desativado_localmente` | **existe** (mig 0098), guarda implementada em `usuarios_import` (§4.1) | o import não reativa mais quem foi desligado localmente |
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
  e-mail seguem só no create — D6c em revisão pelo dono). Desde 05/10/2026 reconcilia só
  `FORMADOR`: `COORD_ACOMPANHA` saiu da tela e as linhas antigas ficam como estão.

### 3.2 🟡 RECLASSIFICADO — o núcleo sobrevive, refatorar (não apagar)

| item | verdade que sobra | o que a auditoria errou |
|---|---|---|
| **`DATCoordenador`** | cadastro paralelo: 12 campos de conteúdo, **sem FK de identidade** para `Usuario`. Refatorar p/ `(usuario_fk, area)` resolvendo por CPF (épico #1833) | "o importer preenche todos" — **falso**; grava 4 (`_apply_dat_coordenador` em `export_contract_importer.py`) |
| `AcaoDAT` | endpoint `/dat/acoes/` é candidato a deprecação (nenhuma tela React lê) | comentário "LEGACY" está **certo**; o model **é escrito** pelo import (`_process_row` em `dat_cadastros_import.py`); são 2 serializers, não 1 |
| `DATCompra` | só `valor_unitario`/`qtd_utilizada` são digitação manual | `quantidade` **é importada e load-bearing** no cálculo de códigos. Manter |
| `DATFormacao` | só "sem importador em lote" | 29 campos (não 24); CRUD vivo; domínio distinto. Manter |
| pares status/data (`dat_registro.py`) | **manter os 7** | conflacionou `DATRegistro` (emite 7) com `DATCadastro` (4 colunas) |

### 3.3 🔴 REFUTADO — NÃO AGIR

| afirmação | por que caiu (evidência) |
|---|---|
| "~20 classes RBAC mortas" | **load-bearing.** `test_every_matrix_key_has_policy_class` (`test_rbac_policies.py`) obriga uma classe `Can*` por key de `ACCESS_POLICIES`; `GET /api/me/policies/` (`MePoliciesView` em `views/me.py`, rota `me-policies` em `urls.py`) é **contrato público do frontend**. Apagar quebra o teste **e** o contrato |
| "`RegistroConclusaoAcao`/`RegistroAncora` mortos" | **vivos** — persistência de dois endpoints; a view chama o **método** do model (`.registrar_ancora()`, `.concluir()`), não o nome da classe |
| "`Colecao` nunca exposto" | era vivo (import + FK + dashboard); **removido em 06/10/2026**: coleção é a família (`ProjetoGeral`), migração 0118 |
| "`FeriadoLocal` nunca usado" | **vivo** — query em runtime (`get_holidays` em `business_calendar_service.py`), admin, Celery de notificações |
| "varrer os 6 scripts atrás de de-para hardcoded antes de apagar" | **não há** `SETOR_DO_PROJETO`; o único alias (`IDEB`→Gestão Escolar) já vive em `normalize_projeto_name` (`resolvers.py`). Os 6 scripts são **seguros de remover** |

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

O PR #1886 (`is_active` no update) foi o **primeiro degrau**; `desativado_localmente`
(migration 0098, #1894) é o segundo e **já está implementado** — a guarda vive em
`usuarios_import` (não reativa quem tem a flag) e tem teste dedicado
(`test_desativado_localmente_1894.py`).

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
COORDENADOR**. As pessoas de SUPORTE/OPERACIONAL veem a grade (`view_all_availability`) via o
pacote do perfil DAT, pelo vínculo `EQUIPE`/`GERENTE` na gerência DAT — não via grupo (desde o
PR 12 o grupo não dá poder).

**DECIDIDO (dono, 05/10/2026):** essas pessoas ganham o papel `EQUIPE` ("Equipe administrativa"),
que só diz "trabalha neste setor" e também serve ao Controle e a outros setores — sem efeito em
lista, escopo ou grupo; desde o PR 12 é esse vínculo `EQUIPE` na gerência DAT que dá o pacote do perfil
(o grupo DAT sozinho não dá a grade). Regra completa em [`rbac.spec.md`](specs/backend/rbac.spec.md).

---

## 5. GCal — a resposta que decide a viabilidade da §4.2

**Pergunta (sheets.banco):** re-publicar um evento já no Google Agenda **atualiza** ou
**duplica**?

**MEDIDO — ATUALIZA, não duplica.** O `eventId` é **determinístico por Solicitação**
(`_event_id_for` em `services/gcal/validation.py` → `{PREFIX}-{id}`), e o sync decide
(`upsert_one` em `services/gcal/sync.py`): aprovado + evento existe (ou adota) → **UPDATE**;
não existe → CREATE; não-aprovado com id → DELETE.

**Consequência:** a parte 3 da transferência (§4.2) é **viável com a máquina que já
existe** — se a troca editar os participantes da **mesma** solicitação (mesmo id) e
re-sincronizar, o convite é **atualizado** (attendees passam ao sucessor), sem duplicar.
Não é preciso passo manual. ⚠️ Só vale editando as solicitações existentes; **criar novas**
solicitações criaria eventos novos.

---

## 6. O de-para de setor no sistema

O predicado do gate D6 recomendado pelo sheets.banco comparava **setor canônico** dos dois
lados (não igualdade de gerência — igualdade barraria 46% da operação).

**Superado no PR 9 das permissões (16/10/2026).** O escopo ficou pela **gerência do projeto**,
não pelo setor:

1. `Gerencia.setor_canonico` — existe (migration 0099) e é populado pelo import, mas não dá
   escopo: o lint V006 proíbe o setor nos arquivos de escopo;
2. `projeto.gerencia` — a medição de 2026-08-26 (124/125 vazio) é histórica; hoje há 0 projetos
   ativos sem gerência em produção (`ACHADOS_REAIS`, M10-04);
3. o predicado — `solicitacao_scope.py` filtra por `projeto__gerencia_id`;
   `participantes_fora_da_gerencia` (P9-5) só aceita participante com vínculo vigente com escopo
   (papel ≠ `EQUIPE`) na gerência do projeto, e só se quem cria tem papel GERENTE/COORDENADOR/APOIO
   nela; fail-closed (projeto sem gerência ou criador sem papel lá → todos fora). Global/privilegiado
   (superuser, Superintendência, Controle, DAT) é isento.

SSOT: `services/solicitacao_scope.py` e [`rbac.spec.md`](specs/backend/rbac.spec.md).

---

## 7. Sequenciamento e estado

| # | tarefa | estado |
|---|---|---|
| 1 | `_update_formadores` (`is_active` + COORD_ACOMPANHA) | ✅ **PR #1886** (gate 8/8); desde 05/10/2026 só `FORMADOR` |
| 2 | remover os 6 scripts de raspagem | pronto (§3.3: seguro) |
| 3 | migrations: `setor_canonico` ✅ (0099), `desativado_localmente` ✅ (0098); papel `EQUIPE` ✅ (05/10/2026); falta `projeto_geral` | parcial |
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
