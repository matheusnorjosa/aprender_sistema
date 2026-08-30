---
status: canonical
last_verified: 2026-08-28
audit_baseline: 90f6a048
last_runtime_reverification: d08acfa5 (2026-07-20)
last_v0_revalidation: f6eecd5f (2026-08-19; revalidação por código+git dos 46 itens `aberto`)
last_code_reconciliation: d8e64714 (2026-08-25; código + git + estado de issue de todo item `aberto`/`parcial`)
last_confirmed_production_snapshot: 94f27651 (2026-07-20; estado atual não verificado)
sources_of_truth:
  - v2/docs/audits/2026-07-17-system-module-audit.md
  - reverificação por execução contra main d08acfa5 (2026-07-20)
  - reconciliação parcial por código, testes e histórico Git contra main 6d73ba29 (2026-08-17)
  - reconciliação por código, histórico Git e estado de issue contra main d8e64714 (2026-08-25)
---

# Achados reais — auditoria modular M00–M28

> **Este é o documento vivo.** Atualize-o conforme cada achado for resolvido.
> O relatório da investigação (`2026-07-17-system-module-audit.md`) é histórico e imutável:
> guarda as 498 hipóteses, os vereditos e os erros do processo. Aqui ficam só os achados que
> **sobreviveram à refutação** e o último status conhecido de cada um.
>
> **Escopo da atualização de 2026-08-17:** esta passagem reconciliou onze itens com o
> `HEAD 6d73ba29` — seis resolvidos no escopo do ID e cinco parciais — e executou os testes
> frontend diretamente relacionados. Os outros 46 itens **não foram reexecutados**; seu
> status `aberto` continua sendo o último veredito de 2026-07-20, não uma nova afirmação
> sobre a produção atual.
>
> **Escopo da atualização de 2026-08-25 (mais recente):** reconciliação por código, histórico
> Git e estado de issue contra o `HEAD d8e64714`. Ver
> [Reconciliação de 2026-08-25](#reconciliação-de-2026-08-25-head-d8e64714). Continua **não
> sendo verificação de deploy**: nada foi promovido a `em prod` nesta passagem.

## Como este documento nasceu

1. Auditoria modular de 29 módulos sobre o commit `90f6a048` → **498 hipóteses brutas**.
2. Pente fino adversarial: cada achado confrontado por um refutador; P0/P1 por um segundo
   cético independente → **P0 11→5, P1 181→52**, 224 notas trocadas, 4 refutados.
3. Reverificação por execução contra `main d08acfa5`, com os fatos reais do ambiente
   confirmados pelo dono → o que está abaixo.

A auditoria original **acertava os mecanismos e errava as consequências**. Por isso as
severidades daquele relatório não valem: valem as desta tabela.

### Limites de integridade do dossiê histórico

O arquivo histórico preserva o processo como ele ocorreu; ele não foi reescrito para parecer
mais completo do que é. A validação de 2026-08-17 encontrou:

- catálogo nominal completo de M00 a M28 e dossiês para os 29 módulos;
- trechos fisicamente truncados em resumos de M19–M28 e em várias células longas de evidência;
- métricas de etapas diferentes que não reconciliam entre si: 498 hipóteses, 495 vereditos,
  493 severidades originais e 489 severidades finais;
- uma consolidação intermediária que diz não ter recebido M24–M28, embora dossiês posteriores
  desses módulos tenham sido anexados.

Essas limitações não apagam os mecanismos provados, mas impedem usar o relatório histórico
como corpus exaustivo ou fila atual. Os status abaixo prevalecem e cada correção futura deve ser
revalidada contra o `HEAD` e, quando aplicável, contra produção.

## Situação histórica em 2026-07-20

| | Qtd |
|---|---:|
| **P0 — vivos em produção** | **2** |
| P1 | 36 |
| P2 | 19 |
| **Total acionável** | **57** |
| Já corrigidos (não viram issue) | 4 |

Baseline da auditoria: `90f6a048`. Produção: `94f27651`. `main`: `d08acfa5`.
Os 57 achados abaixo formavam a fila reconfirmada naquele corte. Essa frase não deve ser
projetada sobre o `HEAD` ou a produção atuais.

## Reconciliação parcial em 2026-08-17

| Situação no `HEAD 6d73ba29` | P0 | P1 | P2 | Total |
|---|---:|---:|---:|---:|
| Resolvidos no escopo do ID | 2 | 3 | 1 | **6** |
| Correção parcial, com residual documentado | 0 | 4 | 1 | **5** |
| Sem revalidação individual no `HEAD` | 0 | 29 | 17 | **46** |
| Total histórico da fila | 2 | 36 | 19 | **57** |

Esta é uma reconciliação de código e testes no repositório, não uma verificação de deploy.
Por isso nenhum item novo foi marcado `em prod`. A soma 51 (parciais + não revalidados) **não**
é uma contagem de defeitos vivos em produção; o total acionável atual é indeterminado até a
revalidação dos 46 restantes.

## Revalidação V0 em 2026-08-19 (Onda V0 executada)

Os **46 itens `aberto`** foram revalidados individualmente contra o `HEAD f6eecd5f`, por
**código + git history + estado de issue/PR** (fan-out de 12 agentes, com verificação
adversarial nos `resolvido` de alta severidade). **Não é verificação de deploy** — itens
dependentes de nginx/DR/dados de prod seguem precisando de observação read-only em produção.

| Veredito no `HEAD f6eecd5f` | Qtd |
|---|---:|
| **LIVE** — mecanismo ainda presente no código | **39** |
| **parcial** — sintoma principal mitigado por PR recente, com residual | **6** |
| **resolvido** — mecanismo não existe mais | **1** |

### Reclassificados nesta passagem (7 dos 46)

| ID | Sev. | Antes | Agora | PR/commit | Residual |
|---|---|---|---|---|---|
| `M12-15` | P2 | aberto | **resolvido** | #1760 (`9328227f`) | — (issue CLOSED; ownership do state pelo cache) |
| `M03-03` | P1 | aberto | **resolvido** | #1758 (`9ae753e6`) | sub-ponto de IP no edge herda de `M01-01`/#1660 (não é código deste ID) |
| `M12-19` | P1 | aberto | **parcial** | #1750 (`cdbc0d0c`) | paginação/total/dedup/backoff OK; residual: publish trata HTTP 202 como concluído |
| `M15-02` | P1 | aberto | **parcial** | #1762 (`2f36b303`) | serializer + clamp do dashboard OK; falta CHECK-constraint no banco + datafix |
| `M15-03` | P1 | aberto | **parcial** | #1764 | `external_hash` imutável no PATCH + `quantidade>0`; falta identidade natural-key + UniqueConstraint |
| `M23-02` | P1 | aberto | **parcial** | #1735 (`20c6f48d`) | redação de CPF na escrita+leitura OK; resíduo teórico (username não-CPF por design) |
| `M05-03` | P2 | aberto | **parcial** | #1572 (`a545d5f8`) | metade reverse-m2m corrigida; sintoma titulado (delete de Group deixa ex-membros stale) segue LIVE |

O workflow ligou PR→achado **mesmo sem auto-close** da issue (M12-19/M23-02) e distinguiu
"PR tocou o arquivo só por outro motivo" (M10-06/#1699 PII, M08-12/#1680 erro genérico) — sem
falso-resolvido. Os 5 PRs desta leva (#1758/#1760/#1761/#1762/#1764) mais LGPD/RBAC anteriores
respondem por esses 7.

### Os 39 que seguiam LIVE em 2026-08-19 (mecanismo no `HEAD f6eecd5f`, issue OPEN naquela data)

> **Veredito de 2026-08-19, superado.** Esta lista é o corte daquela data e fica como registro.
> A reconciliação de 2026-08-25 mediu que **20 dos 39** mudaram de estado no código desde então
> (18 `resolvido`, 2 `parcial`). Para o estado corrente, ler
> [Reconciliação de 2026-08-25](#reconciliação-de-2026-08-25-head-d8e64714) e a coluna `Status`
> da fila adjudicada — não esta lista.

`M01-01` `M01-07` `M02-09` `M03-02` `M04-01` `M04-05` `M05-07` `M06-04` `M07-01` `M07-02`
`M08-01` `M08-07` `M08-09` `M08-12` `M09-05` `M10-01` `M10-02` `M10-03` `M10-04` `M10-05`
`M10-06` `M10-07` `M11-04` `M14-01` `M14-02` `M14-03` `M14-05` `M15-04` `M15-05` `M15-08`
`M15-09` `M16-04` `M17-01` `M18-05` `M18-06` `M22-14` `M26-02` `M26-03` `M27-24`

> ⚠️ **`M07-01`/`M07-02` — reclassificar severidade (era P1):** `get_assignable_group_names`
> (`services/rbac_service.py:41-50`) libera todo grupo `SETOR`/`FUNCAO` — inclui **Superintendência
> (SETOR) + Gerente (FUNCAO)**, o combo aprovador (PA: `superuser OU Gerente+Superintendência`).
> `validate_group_ids` (`serializers/usuario.py:243-263`) só barra auto-modificação e alvo superuser
> — **não** barra montar o combo. Um portador de `manage_admin_registries` (DAT, não-superuser) cria
> conta com senha + [Gerente, Superintendência] = **escalonamento a aprovador**. Mecanismo LIVE
> (verificado 2026-08-19). A auditoria tratava a escopagem ator×alvo do admin de usuários como
> **decisão de policy pendente (G2)**, não descuido — daí P1; decidir se vira P0.
>
> **Atualização de 2026-08-25 — mecanismo fechado no código.** `a81053cd` (#1769, 2026-08-19)
> introduziu a policy ator×alvo no admin de usuários; issues #1616 e #1617 estão CLOSED. A
> pergunta de severidade (P1 → P0) ficou **sem resposta** e perdeu urgência com a correção: não
> foi decidida nem promovida aqui. Deploy não verificado.

**Total acionável no corte de 2026-08-19 (por código, não deploy): 45** (39 LIVE + 6 parciais
com residual). Os `resolvido` deixam de contar. Épicos-causa-raiz (V2) inalterados naquele corte.

> ⚠️ **Aritmética inconsistente dentro da própria passagem V0, não corrigida aqui.** A tabela de
> vereditos soma 39 LIVE + 6 `parcial` + 1 `resolvido` = 46, mas a tabela «Reclassificados nesta
> passagem» lista **2** `resolvido` (`M12-15`, `M03-03`) e **5** `parcial` — ou seja, 39 + 5 + 2.
> O total 45 herda a contagem de 6 parciais. Registrado como defeito do registro V0; os números
> ficam como foram publicados, e o estado corrente vem da seção seguinte, não daqui.

## Reconciliação de 2026-08-28 (round-trip / entrada-direta)

Duas auditorias por fan-out sobre o `HEAD d4beda07`: **cobertura** (página×dado×endpoint, as 46
rotas de `AppRoutes.tsx`) e **round-trip** (`form → write-serializer → model → read/List-serializer
→ tela`, ~20 entidades). Motivadas pela meta "todos os dados aparecendo nos campos certos, por
import E por entrada direta". Método: cada achado é hipótese com file:line; os graves (🔴 de perda
ativa) foram **re-verificados adversarialmente** antes de virar issue, e **cruzados contra os
M-codes existentes** — o crosscheck evitou ~8 issues duplicadas (a maioria dos ~15 achados de
round-trip já eram M-codes abertos). `resolvido` = mergeado; nada promovido a `em prod`.

**Re-confirmados VIVOS (M-codes existentes; evidência fresca 2026-08-28):**

| ID | Achado | Evidência 2026-08-28 (file:line) | Issue |
|---|---|---|---|
| `M18-05` | DATCoordenador `data_admissao` zerada a CADA edição (**perda ativa**) | List omite (`serializers/dat_module/dat_coordenador.py:64-85`) → `CoordenadoresPage.tsx:234` seta null → `handleSave:249` PATCH `null` | épico #1654 |
| `M15-09` | DATCompra editar vaza FK entre registros | List omite ids (`dat_module/dat_compra.py:128-150`) + `ComprasPage.tsx:245` sem `resetFields` | #1636 |
| `M10-05` | Solicitacao: COORD_ACOMPANHA/guest não editável | `EditSolicitacaoPage:139-281` só FORMADOR; `MySolicitacoesPage:181` filtra guest | #1627 |
| `M15-10`/FE↔BE | dangling form fields (form≠serializer): DATAcao `area`/`observacoes`, DATCadastro `link_*` | `AcoesPage.tsx:875,988`; `CadastrosPage.tsx:760,765` | épico #1655 |
| SSOT-part. | `Solicitacao.coordenador` FK nunca capturado + M2M `formadores` morto | `serializers/solicitacao.py:144,170` | épico #1666 |

**Novos (confirmados por reprodução; issue criada; milestone #22):**

| Achado | Verificação | Issue |
|---|---|---|
| `_compute_external_hash` OMITE segmento → 156 eventos colapsam; **MATERIALIZADO no golden (controle positivo 6/6)** | `eventos_import.py:345` (recipe); medido no golden (RELAY 45-48) | **#1915** — **fix**: `segmento` na chave natural + migração `0101` (re-hash UTC→Fortaleza); **recuperação** dos 156 via re-import segue gated (autorização + dry-run verde) |
| ~~`ano` fora de form/serializer → UI-create cai em `ano=NULL` → 2º create colide (400)~~ → **resolvido** por #1925 (BE: `ano` gravável nos write-serializers) + #1927 (FE: input Ano nos forms de create) | DATRegistro/Cadastro/Acao | #1912 |
| edição inline de Acompanhamento/Prova morta (backend pronto, front não liga `onClick`) | `PlanoFormacoesPage.tsx:69-70` | **#1913** — **fix** (front liga o `onClick` de Acompanhamento/Prova; célula clicável com label): PR #1922 |
| `setor_canonico`/`Projeto.setor`/`ProjetoGeral` sem entrada-direta (`setor_canonico` gateia navegação) | `serializers/organizacao.py`; `usePermissions.ts:86` | #1914 |

O achado do hash (#1915) atualiza a memória `hash-dedup-key-must-cover-natural-key` de **latente**
para **materializado no golden**. Segue **não sendo verificação de deploy**.

## Reconciliação de 2026-08-25 (`HEAD d8e64714`)

O arquivo não era tocado desde `9631ef60` (2026-08-19). Entre aquele commit e o `HEAD`
entraram **74 commits, 27 deles `fix(...)`**, e **nenhum** atualizou este documento. Esta
passagem só reconciliou o registro; não corrigiu código.

**Método, por ID marcado `aberto` ou `parcial`:** (1) estado da issue via
`gh issue view <N> --json state`; (2) estado do código via `git log --grep="<ID>"` e leitura do
artefato citado; (3) os dois são registrados separadamente porque **divergem**.

**Limite herdado, mantido:** isto continua sendo reconciliação de código e histórico Git.
`resolvido` aqui significa *mergeado na `main`* — **não** significa `em prod`. Nenhum item foi
promovido a `em prod` nesta passagem, e o último snapshot de produção confirmado segue sendo
`94f27651` (2026-07-20).

### Contradição interna corrigida

Até esta passagem, os **7 IDs reclassificados na passagem V0** continuavam lendo `aberto` na
coluna `Status` da fila adjudicada: `M12-15` e `M03-03`, que o próprio arquivo declarava
`resolvido`, e `M12-19`, `M15-02`, `M15-03`, `M23-02`, `M05-03`, declarados `parcial`. Quem lesse
só a tabela — o modo normal de consumo — recebia `aberto` para dois achados que o mesmo arquivo
dizia estarem fechados. A coluna `Status` agora reflete o veredito.

### Mudaram de estado: 31 IDs

A coluna **Issue** registra o estado no GitHub; a coluna **Commit** registra o estado do código.
Onde a issue é um épico que cobre outros IDs, ela pode seguir OPEN com o ID já fechado.

| ID | Sev. | Veredito do árbitro (2026-08-19) | Estado do código (`d8e64714`) | Commit (data) | Issue |
|---|---|---|---|---|---|
| `M01-01` | P2 | LIVE | resolvido | `d24da3df` (2026-08-20) | #1660 CLOSED |
| `M01-07` | P1 | LIVE | resolvido | `aa8bfb5c` (2026-08-20) | #1612 CLOSED |
| `M03-02` | P2 | LIVE | resolvido | `9da4674d` (2026-08-20) | #1648 CLOSED |
| `M03-03` | P1 | resolvido (só no texto) | resolvido | `9ae753e6` (2026-08-18) | #1614 CLOSED |
| `M03-10` | P2 | parcial (2026-08-17) | resolvido | `20c6f48d`+`d2f226cc` (2026-08-18) | #1657 CLOSED |
| `M05-03` | P2 | parcial | resolvido | `01ddb4cd` (2026-08-21) | #1667 CLOSED |
| `M06-04` | P2 | LIVE | resolvido | `88626736` (2026-08-19) | #1661 CLOSED |
| `M07-01` | P1 | LIVE | resolvido | `a81053cd` (2026-08-19) | #1616 CLOSED |
| `M07-02` | P1 | LIVE | resolvido | `a81053cd` (2026-08-19) | #1617 CLOSED |
| `M07-03` | P1 | parcial (2026-08-17) | resolvido | `11219a7e` (2026-08-18) | #1618 CLOSED |
| `M08-01` | P1 | LIVE | resolvido | `af2e8810` (2026-08-19) | #1619 CLOSED |
| `M08-07` | P2 | LIVE | resolvido | `cd60882a` (2026-08-21) | #1664 OPEN (épico) |
| `M08-09` | P2 | LIVE | resolvido | `a986a250` (2026-08-21) | #1664 OPEN (épico) |
| `M09-06` | P1 | parcial (2026-08-17) | resolvido | `659c164f` (2026-08-18) | #1622 CLOSED |
| `M10-01` | P1 | LIVE | resolvido | `824f777c` (2026-08-20) | #1623 CLOSED |
| `M10-02` | P1 | LIVE | resolvido | `a1577d41` (2026-08-19) | #1624 CLOSED |
| `M10-03` | P1 | LIVE | resolvido | `f115dd45` (2026-08-19) | #1625 CLOSED |
| `M10-04` | P1 | LIVE | **parcial** | `185fab4a` (2026-08-20; só o shape do create) | #1626 CLOSED |
| `M11-04` | P2 | LIVE | resolvido | `59b001e5` (2026-08-19) | #1650 CLOSED |
| `M12-15` | P2 | resolvido (só no texto) | resolvido | `9328227f` (2026-08-19) | #1652 CLOSED |
| `M12-19` | P1 | parcial (residual: publish tratava HTTP 202 como concluído) | resolvido | `3ab590d6` (2026-08-20) | #1629 CLOSED |
| `M14-01` | P2 | LIVE | **parcial** | `2818a2ad` (2026-08-24) | #1656 OPEN (épico) |
| `M14-02` | P1 | LIVE | resolvido | `4321d90b` (2026-08-20) | #1630 CLOSED |
| `M14-03` | P2 | LIVE | resolvido | `4f63caf0` (2026-08-21) | #1663 OPEN (épico) |
| `M15-02` | P1 | parcial | **parcial** (inalterado) | `5f78a59b` (2026-08-19) | #1632 OPEN |
| `M15-03` | P1 | parcial | **parcial** (inalterado) | `f6eecd5f` (2026-08-19) | #1633 OPEN |
| `M16-07` | P1 | parcial (2026-08-17) | resolvido | `1fbcb34b` (2026-08-18) | #1638 CLOSED |
| `M18-06` | P2 | LIVE | resolvido | `062df0ec` (2026-08-20) | #1653 CLOSED |
| `M23-02` | P1 | parcial (resíduo teórico) | **parcial** (inalterado) | `20c6f48d`+`d2f226cc` (2026-08-18) | #1644 CLOSED |
| `M26-02` | P1 | LIVE | resolvido | `3bca74f3` (2026-08-21) | #1645 CLOSED |
| `M27-24` | P1 | LIVE | resolvido | `88626736` (2026-08-19) | #1647 CLOSED |

Nove desses 31 são só correção de contradição do registro: `M03-03`, `M12-15`, `M15-02`,
`M15-03` e `M23-02` já tinham veredito na passagem V0 e a tabela contradizia o texto;
`M03-10`, `M07-03`, `M09-06` e `M16-07` eram parciais de 2026-08-17 nunca reabertos. Os outros
**22** são mudança real de estado do código depois do corte da V0.

### Residuais que sustentam os `parcial` desta leva

- **`M10-04`** — rebaixado de `resolvido` para `parcial` na revisão de 2026-08-25, porque
  `185fab4a` (#1778, 2026-08-20) validou o **shape**, nunca o alvo. `_ExtraParticipantsSerializer`
  (`v2/backend/apps/core/views_solicitacao.py:53-77`) limita cada lista a 200 itens, exige inteiro
  positivo em `formador_ids`/`coord_acompanha_ids` e e-mail válido nos `*_emails`, e
  `_create_participants` passou a filtrar `is_active=True` (`views_solicitacao.py:378` e `:384`).
  Nada verifica **quem** são os ids: qualquer usuário ativo vira `FORMADOR`/`COORD_ACOMPANHA` e
  qualquer e-mail válido vira `guest_email`, sem policy ator×alvo em lugar nenhum do caminho. O
  próprio corpo do commit delimita o escopo — "a policy ator×alvo por participante (épico #1656)
  fica fora". Fechou "sem limite e estoura 500"; **"aceita alvo arbitrário sem policy" segue LIVE**.
- **`M14-01`** — `2818a2ad` (#1824) fechou só o ramo de vigência: `HasSectorAccess` passou a usar
  `EquipeGerencia.vigentes_em()` (`v2/backend/apps/core/rbac/permissions.py:300-311` e `:319-327`),
  então ex-membro expirado perde o gate. O mecanismo titulado **segue LIVE**: sem `gerencia_id`,
  qualquer papel com vínculo vigente entra — a query não filtra papel (`permissions.py:301-307`).
- **`M15-02`** / **`M15-03`** — sem mudança desde a V0. Falta, respectivamente, `CHECK`-constraint
  no banco + datafix, e identidade natural-key + `UniqueConstraint`.
- **`M23-02`** — issue #1644 está CLOSED e a redação de CPF existe na escrita e na leitura, mas o
  veredito de 2026-08-19 registrou resíduo teórico (username não-CPF por design). Mantido
  `parcial` porque **quem baixou o status foi o árbitro**, com a evidência à mão; promover a
  `resolvido` aqui seria sobrescrever um veredito sem prova nova.
- **`M15-10`** — inalterado desde 2026-08-17: só a Fase A (`8f894279`, 2026-08-11, e `e94f15f4`,
  2026-08-12); issue #1637 segue OPEN e a Fase B continua sem desenho.

### Seguem `aberto`: 17 IDs

Issue OPEN **e** nenhum commit citando o ID ou a issue (`M04-05` saiu: **resolvido em #1852**, parse `dry_run` fail-closed; `M02-09` saiu: **resolvido** (issue #1613 — resolvers rejeitam ambiguidade + norm simétrica no import DAT); ambos posteriores a esta reconciliação):

`M04-01` `M05-07` `M08-12` `M09-05` `M10-05` `M10-06` `M10-07` `M14-05`
`M15-04` `M15-05` `M15-08` `M15-09` `M16-04` `M17-01` `M18-05` `M22-14` `M26-03`

Amostra reverificada no artefato, não só por ausência de commit:

- `M04-05` — ✅ **resolvido em #1852** (posterior a esta reconciliação): o parse migrou para o
  helper fail-closed `apps.core.imports.request_params.parse_dry_run` nos 12 sítios; valor
  desconhecido (`dry_run=maybe`) agora permanece em dry-run (preview), não mais APPLY.
- `M16-04` — nenhum `select_for_update` nas views/serializers DAT; o lost update continua.
- `M26-03` — `v2/infra/scripts/test_dr.sh` não é tocado desde `ca9c1c37` (#1006) e não menciona
  `.age`. A cobertura de `.age` ficou toda em `v2/infra/scripts/tests/restore_db.bats`, que é
  outro artefato e não é o round-trip de DR ponta a ponta que o ID pede.
- `M04-01` — `v2/backend/apps/core/services/equipe_gerencia_import.py` mudou por `2818a2ad`
  (2026-08-24) e **só** por vigência de vínculo (`valid_from`/`valid_to`); antes dele o arquivo
  estava parado desde `45c11902` (2026-07-30). `ac418a50` (2026-08-25) resolve coordenador por CPF,
  mas em `export_contract_importer.py` e `controle_acoes_import.py` — **não toca** este arquivo
  (`git show --stat --format="" ac418a50`). A duplicação de Gerência não foi tocada por nenhum dos
  dois. Exemplo de por que "arquivo mudou" não é "achado fechado".
- `M10-05` — o commit de `M10-04` (`185fab4a`) declara no corpo que a reconciliação de
  participantes no update fica **fora do escopo**. Ausência de fix confirmada pela própria PR.

**Total acionável por código (não deploy): 25** — 19 `aberto` + 6 `parcial`
(`M10-04`, `M14-01`, `M15-02`, `M15-03`, `M15-10`, `M23-02`). Era 45 no corte de 2026-08-19.

### Divergência de severidade com a auditoria-mãe — observada, não resolvida

O árbitro já declara que "as severidades daquele relatório não valem: valem as desta tabela", e
diverge da auditoria de 2026-07-17 na severidade de **27 dos 61 achados**. Esta passagem
**não mexeu em nenhuma severidade** e não tentou reconciliar as duas escalas. Onde a divergência
ficou mais visível: o quadro `M07-01`/`M07-02` (P1 com uma pergunta P0 deixada em aberto, agora
sem urgência porque o mecanismo foi fechado) e os `M26-0x`, que aqui são P1 mas pendem do épico
#1662, classificado P0. Fica para uma passagem própria, com o critério de severidade explicitado
antes de qualquer reclassificação.

## Legenda de status

| Status | Significado |
|---|---|
| `aberto` | o último corte confirmou o defeito e não há correção registrada; pode exigir nova revalidação |
| `em andamento` | PR aberta |
| `parcial` | o sintoma principal foi mitigado, mas há residual funcional, de cobertura ou de dados |
| `resolvido` | corrigido e mergeado — anote o commit e a data |
| `em prod` | correção deployada e verificada em produção |
| `descartado` | reclassificado ou refutado depois — anote o porquê |

## Fila adjudicada — status reconciliado em 2026-08-25 (`HEAD d8e64714`)

A coluna `Status` é o estado **do código na `main`**; nenhuma linha afirma estado de produção.
A coluna `Issue` traz o número da issue e — **onde o estado foi conferido nesta passagem** — o
estado dela no GitHub, porque os dois divergem: um épico pode seguir OPEN com o ID já fechado
(`M08-07`, `M08-09`, `M14-03`), e uma issue pode estar CLOSED com residual registrado aqui
(`M23-02`).

**Alcance real da conferência, para não prometer mais do que foi feito.** O método desta passagem
rodou `gh issue view` **apenas** nos IDs marcados `aberto` ou `parcial` e nos reclassificados. As
**11** linhas que já estavam `resolvido` antes dela não foram reconferidas e por isso trazem só o
número, sem `(OPEN)`/`(CLOSED)`: `M03-01`, `M26-01`, `M03-11`, `M05-05`, `M10-08`, `M15-11`,
`M16-08`, `M17-02`, `M19-01`, `M19-02` e `M19-03`. Célula sem estado significa **não conferido
neste corte** — não "sem issue" e não "issue aberta".

`Resolvido em` cita commit **e** data — linha sem os dois não é `resolvido`. Célula com mais de um
commit traz a data **de cada commit**, porque eles podem estar a semanas de distância (em `M05-03`,
`a545d5f8` é de 2026-07-18 e `01ddb4cd` de 2026-08-21).

| ID | Sev. | Status | Título | Ator real | Issue | Resolvido em |
|---|---|---|---|---|---|---|
| `M03-01` | **P0** | resolvido | rbac/imports: import de usuários permite auto-escalação a Gerente+Superintendência | DAT (3 contas ativas no censo de 2026-07-20) | #1610 | `ccbe1e05` (2026-07-30) |
| `M26-01` | **P0** | resolvido | infra/DR: restore_db.sh roda `gzip -t` antes de decifrar e rejeita todo backup .age de produção | Operador/SRE com acesso à VM de banco | #1611 | `8f392636` (2026-08-10) |
| `M01-07` | **P1** | resolvido | rbac/admin: salvar grupo revoga membros alem dos 100 primeiros (paginador global ignora page_si… | Superuser (1 ativo em prod) para a perda de dados no editor de grupos … | #1612 (CLOSED) | `aa8bfb5c` (2026-08-20) |
| `M02-09` | **P1** | **resolvido** | imports/resolvers: rejeitar ambiguidade em vez de escolher com .first(), e corrigir normalizaçã… | DAT (3 ativos) e Superintendência (1 ativo) + superuser (1). Os endpoi… | #1613 | `resolve_projeto`/`resolve_tipo_evento` rejeitam ambiguidade (`_pick_unique`) + import DAT usa `resolve_projeto` (norm simétrica). Substring de PESSOA (`resolve_user_by_name`) segue em `M22-14`/#1643 |
| `M03-03` | **P1** | resolvido | auth: lockout e throttle de login sao evadiveis por grafia do CPF e por sessao autenticada | Qualquer um dos 148 usuarios ativos autenticados (nenhum grupo necessa… | #1614 (CLOSED) | `9ae753e6` (2026-08-18) |
| `M03-11` | **P2** | resolvido | frontend/auth: `checkAuth` e o boot (App.tsx) deslogam a sessão em QUALQUER erro (5xx/rede), não só 401/403 — um blip transitório manda um usuário com cookie válido para a tela de login (auditoria dinâmica 2026-08-17, F2). Fix: `checkAuth` relança erro não-auth; App mostra tela de erro com retry; `UsuariosPage` fail-closed | Qualquer usuário autenticado (o boot roda em todo carregamento da app) | #1741 | `fcc074b1` (2026-08-18) |
| `M04-01` | **P1** | aberto | imports/equipe-gerencia: import cria Gerência duplicada para "Brincando" e "Ed Financeira" e de… | DAT (3 membros ativos nao-superuser) + superuser (1). O endpoint POST … | #1615 (OPEN) | — |
| `M07-01` | **P1** | resolvido | rbac/admin: DAT faz takeover de conta aprovadora (senha, desativação e hard delete) | — | #1616 (CLOSED) | `a81053cd` (2026-08-19) |
| `M07-02` | **P1** | resolvido | RBAC/admin de usuarios: DAT faz takeover de conta aprovadora (senha, e-mail, desativacao e hard… | DAT — 3 membros ativos nao-superuser. Probe confirma que DAT e o UNICO… | #1617 (CLOSED) | `a81053cd` (2026-08-19) |
| `M07-03` | **P1** | resolvido | RBAC/Auditoria: registrar AuditLog em todas as mutações de identidade do UsuarioAdminViewSet | 3 usuários ativos do grupo DAT no censo de 2026-07-20 | #1618 (CLOSED) | `aba033f1` (2026-07-31)+`11219a7e` (2026-08-18) |
| `M08-01` | **P1** | resolvido | disponibilidade: PATCH transfere bloqueio aprovado para usuário arbitrário, sem policy nem Audi… | — | #1619 (CLOSED) | `af2e8810` (2026-08-19) |
| `M08-12` | **P1** | aberto | imports/eventos: import de eventos grava solicitacao aprovada sem hard gate de disponibilidade … | Grupo DAT (3 membros ativos nao-superuser) + 1 superuser ativo. `Permi… | #1620 (OPEN) | — |
| `M09-05` | **P1** | aberto | Deslocamentos: UI exige delegacao que o backend nega — Coordenador nao consegue registrar nenhu… | Coordenador (42 ativos) e o ator principal: 100% dos creates pela UI f… | #1621 (OPEN) | — |
| `M09-06` | **P1** | resolvido | Deslocamentos: filtros Origem/Destino inutilizáveis — página desmonta a cada tecla e o filtro falha | Coordenador, DAT, Controle, Superintendência e superuser | #1622 (CLOSED) | `6d73ba29` (2026-08-12)+`659c164f` (2026-08-18) |
| `M10-01` | **P1** | resolvido | solicitações: Gerente lê, edita e exclui solicitação de qualquer gerência (sem escopo ator×alvo… | Gerente — 9 usuários ativos não-superuser em produção. Ator real e num… | #1623 (CLOSED) | `824f777c` (2026-08-20) |
| `M10-02` | **P1** | resolvido | solicitação: troca de projeto para fluxo SUPER mantém status aprovado (lavagem de aprovação, vi… | — | #1624 (CLOSED) | `a1577d41` (2026-08-19) |
| `M10-03` | **P1** | resolvido | solicitacoes: bloquear edicao e exclusao enquanto gcal_status=PENDING (publica conteudo diferen… | Ator real e amplo: o proprio owner da solicitacao. Em prod isso alcanc… | #1625 (CLOSED) | `f115dd45` (2026-08-19) |
| `M10-04` | **P1** | parcial | solicitacoes: extra_participants aceita alvo arbitrário sem policy, sem limite e estoura 500 | Grande. `create` exige `HasPerm("create_solicitation")` (views_solicit… | #1626 (CLOSED) | `185fab4a` (2026-08-20; só o shape — alvo arbitrário sem policy segue) |
| `M10-05` | **P1** | aberto | solicitacoes: edição não reconcilia participantes — convidados e COORD_ACOMPANHA ficam órfãos e… | Existe e é o fluxo comum: 42 Coordenadores ativos + 9 Gerentes + 1 sup… | #1627 (OPEN) | — |
| `M10-07` | **P1** | aberto | imports/eventos: reimport sobrescreve decisão de aprovação, owner e datas e reporta "unchanged" | DAT (3 membros ativos não-superuser) + superuser (1). `import_spreadsh… | #1628 (OPEN) | — |
| `M10-08` | **P2** | resolvido | solicitações: PATCH (re)atribui município/projeto para par sem Compra — elegibilidade era create-only (auditoria dinâmica 2026-08-17) | Coordenador (42 ativos) e demais criadores editando a própria solicitação | #1738 | `b48aa5f2` (2026-08-18) |
| `M12-19` | **P1** | resolvido | Pré-agenda: polling estoura o throttle do operador e a lista mostra total inalcançável | Sim. Rota `/pre-agenda` e `/controle/pre-agenda` sao gateadas por `Req… | #1629 (CLOSED) | `cdbc0d0c` (2026-08-18)+`3ab590d6` (2026-08-20) |
| `M14-02` | **P1** | resolvido | Grade mensal: evento com 2+ participantes multiplica CH, codigo e detalhes por participante | Amplo e real. `MonthlyAvailabilityView.permission_classes = [IsAuthent… | #1630 (CLOSED) | `4321d90b` (2026-08-20) |
| `M14-05` | **P1** | aberto | Disponibilidade/Grade Mensal: unificar a população da grade — visão "Todas" usa coorte históric… | Permanentemente: Controle (1 ativo), DAT (3 ativos), superuser (1) — t… | #1631 (OPEN) | — |
| `M15-02` | **P1** | parcial | Compras DAT: validar invariantes de DATCompra (sobreuso, valor negativo, item vazio, produto de… | DAT (3 ativos) + Controle (1 ativo). O gate de create/update do DATCom… | #1632 (OPEN) | `5f78a59b` (2026-08-19; falta CHECK no banco + datafix) |
| `M15-03` | **P1** | parcial | Compras: definir identidade real de `Compra` — hash sobre campos mutaveis duplica linha na corr… | DAT (3 ativos) e Controle (1 ativo) = 4 atores nao-superuser reais, ma… | #1633 (OPEN) | `f6eecd5f` (2026-08-19; falta natural-key + UniqueConstraint) |
| `M15-04` | **P1** | aberto | imports/compras: preview aceita linhas invalidas (quantidade vazia/decimal/negativa, data ausen… | DAT (3 membros ativos nao-superuser) + 1 superuser. O endpoint `POST /… | #1634 (OPEN) | — |
| `M15-05` | **P1** | aberto | imports/compras: usar UF e código do produto na resolução e gravar Compra.produto | DAT (3 membros ativos nao-superuser) + 1 superuser, via POST /api/cont… | #1635 (OPEN) | — |
| `M15-09` | **P1** | resolvido | Compras (DATCompra): edição reassocia material para outro município/projeto silenciosamente | DAT (3 ativos) + Controle (1) + Assistente Administrativo (1, herda Co… | #1636 (CLOSED) | `#1917` (List expõe FK ids) + `#1919` (resetFields no handleEdit) |
| `M15-10` | **P1** | parcial | DAT/Compras: formulário de Nova Compra descarta campos, grava valor zero e esconde o erro | DAT e Superintendência | #1637 (OPEN) | `8f894279` (2026-08-11) + `e94f15f4` (2026-08-12) — Fase A |
| `M15-11` | **P2** | resolvido | hardening de baixo risco consolidado (auditoria dinâmica 2026-08-17): N+1 em `/coordenadores/{id}/alocacoes/` (select_related); índices redundantes de `external_hash` em `core_compra` (3 btrees → 1 + migração); ImportCompras sem magic-bytes (anti-spoofing via `validate_upload`); disconnect Google apaga credencial local mesmo com revoke ≠ 200/400 (preservar p/ retry); aria-label nos botões só-ícone de Deslocamentos; NOTA get_permissions vs @action | DAT/Controle, operador GCal, visitante autenticado | #1742 | `091e6f53`+`99b85952`+`dcecfebf` (2026-08-18) |
| `M16-07` | **P1** | resolvido | DAT Registros: datas do formulário não chegam ao banco | DAT e superuser | #1638 (CLOSED) | `3954e208` (2026-08-11)+`1fbcb34b` (2026-08-18) |
| `M16-08` | **P1** | resolvido | DAT Registros: opções de status da UI divergem dos choices do backend | DAT e superuser | #1639 | `419fe5fd` (2026-08-11) |
| `M17-01` | **P1** | aberto | DAT/imports: card "Importar CADASTROS DAT" grava AcaoDAT legacy, que nenhuma tela le | DAT (3 membros ativos nao-superuser) + 1 superuser. O gate do card e d… | #1640 (OPEN) | — |
| `M17-02` | **P1** | resolvido | DAT (Ações/Cadastros): editar pelo modal apaga silenciosamente as datas do registro | DAT, Controle e Assistente Administrativo | #1641 | `a0553fd7` (2026-08-11) |
| `M19-01` | **P1** | resolvido | DAT/PlanoFormacoes: CH total e anual ficam um PATCH atrasadas ao atualizar formação inline | DAT e superuser | #1642 | `f9e40902` (2026-08-11) |
| `M19-02` | **P2** | resolvido | field-drift form↔serializer: DATFormacao.titulo obrigatório sem Form.Item (400 no create) + Solicitacao.observacoes coage null para allow_null=False (auditoria dinâmica 2026-08-17; instância do épico #1655) | DAT (3 ativos) e Coordenador (42 ativos) criadores | #1739 | `58759ced` (2026-08-18) |
| `M19-03` | **P2** | resolvido | DAT/PlanoFormacoes: excluir plano faz HARD DELETE em cascata de formações/acompanhamentos/provas — inclusive as concluídas (realizada=True, registro histórico) — sem bloqueio, sem soft-delete e sem auditoria (auditoria dinâmica 2026-08-17). Fix: `perform_destroy` bloqueia (409) quando há concluídas + audita a exclusão permitida; UI gateia o botão | Superintendência (`execute_restricted_operations`) + superuser | #1740 | `92ee82af` (2026-08-18) |
| `M22-14` | **P1** | aberto | Import de bloqueios: resolucao por nome com fallback substring cria bloqueio auto-aprovado na a… | Grupo DAT (3 membros ativos nao-superuser) + 1 superuser ativo, via `H… | #1643 (OPEN) | — |
| `M23-02` | **P1** | parcial | auditoria: redigir CPF (`username`) nos AuditLog de LOGIN_FAILED, na escrita e na leitura | DAT (3 ativos), Controle (1), Superintendencia (1), Gerente (9) — 14 n… | #1644 (CLOSED) | `20c6f48d`+`d2f226cc` (2026-08-18; residuo teorico) |
| `M26-02` | **P1** | resolvido | DR: restore_db.sh declara "Restore completed successfully!" com exit 0 apos um restore que perd… | Operador de DR com SSH na VM02 (na pratica o unico superuser/dono). Na… | #1645 (CLOSED) | `3bca74f3` (2026-08-21) |
| `M26-03` | **P1** | aberto | infra/DR: test_dr.sh nao exercita o backup cifrado — round-trip .age via restore_db.sh nunca fo… | Nao e achado de RBAC — nenhum grupo o alcanca e o censo nao muda a sev… | #1646 (OPEN) | — |
| `M27-24` | **P1** | resolvido | frontend/nginx: restaurar os 7 headers de seguranca descartados pelo add_header aninhado | Qualquer visitante nao autenticado / atacante externo — o defeito esta… | #1647 (CLOSED) | `88626736` (2026-08-19) |
| `M01-01` | **P2** | resolvido | seguranca/rede: resolver de IP confia no primeiro X-Forwarded-For, permitindo forjar origem em … | Anonimo na internet (nao requer conta): o caminho /api/ e o unico prox… | #1660 (épico, CLOSED) | `d24da3df` (2026-08-20) |
| `M03-02` | **P2** | resolvido | auth: login aceita requisição cross-origin e emite sessão (login-CSRF) | — | #1648 (CLOSED) | `9da4674d` (2026-08-20) |
| `M03-10` | **P2** | resolvido | PII/LGPD: remover CPF integral de `Usuario.__str__` e redigir `username` nos logs de auditoria | DAT e Controle no censo de 2026-07-20 | #1657 (épico, CLOSED) | `6b35fa40` (2026-08-11)+`20c6f48d` (2026-08-18)+`d2f226cc` (2026-08-18) |
| `M04-05` | **P2** | **resolvido** | imports: valor desconhecido de `dry_run` é tratado como APPLY em 11 views | — | #1649 (OPEN) | #1852 (parse fail-closed `parse_dry_run`, 2026-08-25) |
| `M05-03` | **P2** | resolvido | RBAC: excluir um Group deixa capabilities dos ex-membros em cache por ate 300s | apenas superuser (1 ativo em prod). DELETE /api/grupos/{id}/ e Superus… | #1667 (épico, CLOSED) | `a545d5f8` (2026-07-18)+`01ddb4cd` (2026-08-21) |
| `M05-05` | **P2** | resolvido | RBAC: mudança de Grupo×Capability via API não gera AuditLog e o delta pendente é atribuído ao próximo ator | Somente superuser e operações administrativas | #1657 (épico) | `aba033f1` (2026-07-31) |
| `M05-07` | **P2** | aberto | frontend: HomePage decide criacao de solicitacao por setor/funcao em vez da policy create_solic… | DAT (3 ativos nao-superuser) e Gerente (9 ativos) — ambos existem hoje… | #1655 (épico, OPEN) | — |
| `M06-04` | **P2** | resolvido | frontend/nginx: locations `/`, `/assets/`, imagens e `/health` perdem os 7 headers de segurança | Não é achado de RBAC — o censo de grupos não se aplica. A superfície a… | #1661 (épico, CLOSED) | `88626736` (2026-08-19) |
| `M08-07` | **P2** | resolvido | disponibilidade: filtrar papeis ocupantes tambem na query de eventos existentes (CONVIDADO bloq… | Somente o superuser (1 ativo), via Django admin (`ParticipationAdmin`,… | #1664 (épico, OPEN) | `cd60882a` (2026-08-21) |
| `M08-09` | **P2** | resolvido | Disponibilidade (RD-05): capacidade diaria ignora eventos que cruzam a meia-noite | Qualquer usuario autenticado que crie/edite Solicitacao ou consulte /a… | #1664 (épico, OPEN) | `a986a250` (2026-08-21) |
| `M10-06` | **P2** | aberto | gcal: descrição do evento perde a seção "Equipe" — payload lê formadores/coordenador legados qu… | Qualquer criador de solicitação — Coordenador (42 ativos), Formador (9… | #1666 (épico, OPEN) | — |
| `M11-04` | **P2** | resolvido | aprovação: `ids` em lote sem validação decompõe string em dígitos e aprova alvo não nomeado | — | #1650 (CLOSED) | `59b001e5` (2026-08-19) |
| `M12-15` | **P2** | resolvido | oauth: vincular state do OAuth Google a sessao que o criou (identidade lida do sufixo mutavel) | Atacante precisa mintar um state via /oauth/google/start, que exige Ca… | #1652 (CLOSED) | `9328227f` (2026-08-19) |
| `M14-01` | **P2** | parcial | RBAC/Grade mensal: HasSectorAccess autoriza qualquer papel com vínculo e ignora `ativo` no ramo… | Depende de variável NÃO VERIFICADA. O gate só é alcançável por quem te… | #1656 (épico, OPEN) | `2818a2ad` (2026-08-24; so o ramo de vigencia) |
| `M14-03` | **P2** | resolvido | Disponibilidade: CH Ano na grade mensal soma so o mes consultado e repete o CH Mes | ~14 atores nao-superuser: DAT 3 + Controle 1 + Assistente Administrati… | #1663 (épico, OPEN) | `4f63caf0` (2026-08-21) |
| `M15-08` | **P2** | aberto | DAT/Compras: PATCH concorrente em DATCompra sobrescreve estoque (lost update) e duplo POST cria… | DAT (3 ativos), Controle (1), Assistente Administrativo lotado em Cont… | #1665 (épico, OPEN) | — |
| `M16-04` | **P2** | aberto | DAT: PATCH concorrente perde update (lost update) em ProjetoGeral/DATRegistro | — | #1651 (OPEN) | — |
| `M18-05` | **P2** | aberto | DAT Coordenadores: edicao apaga data_admissao e vaza observacoes entre registros (detalhe/edica… | DAT (3 ativos) e Controle (1 ativo) + o superuser (1). O endpoint exig… | #1654 (épico, OPEN) | — |
| `M18-06` | **P2** | resolvido | Paginação: DRF ignora `page_size` e esconde até 77% das linhas nas telas DAT | DAT (3 ativos) e Superintendência (1 ativo) + 1 superuser — a permissã… | #1653 (épico, CLOSED) | `062df0ec` (2026-08-20) |

## Correções reconciliadas em 2026-08-17, contra o `HEAD 6d73ba29` (commit de 2026-08-12)

> **Snapshot datado, parcialmente superado.** Quatro linhas `parcial` desta tabela foram
> encerradas depois: `M07-03` (`11219a7e`), `M09-06` (`659c164f`), `M16-07` (`1fbcb34b`) e
> `M03-10` (`20c6f48d`+`d2f226cc`), todas em 2026-08-18. O residual descrito na coluna à direita
> é o que existia em 2026-08-17 e é justamente o que aqueles commits fecharam — a coluna fica
> como registro do que foi medido, não como fila. `M15-10` continua `parcial`.

| ID | Resultado | Evidência atual | Regressão/residual |
|---|---|---|---|
| `M03-01` | resolvido no escopo da autoescalação | O import recebe `actor`; somente superuser pode aplicar a coluna `grupos`, e a primitiva `_assign_groups` repete o gate fail-closed. | `test_import_usuarios.py` cobre o ataque HTTP, ator não-superuser, ausência de ator e superuser. O import ainda altera cadastro/`is_active` de alvos não-superuser; esse residual ator×alvo não está encerrado por este ID. |
| `M26-01` | resolvido no código | `restore_db.sh` distingue `.age`, decifra antes de `gzip -t`, usa `pipefail` local e respeita `BACKUP_DIR`. | `restore_db.bats` cobre `.age` válido, corrupção, formato simples, diretório customizado e `--latest`; o drill real de DR continua pendente. |
| `M07-03` | parcial | O serviço transacional passou a auditar grupos, senha e delete. | Criação, alteração cadastral e ativação sem senha/grupo ainda não têm cobertura integral de AuditLog. |
| `M09-06` | parcial | O estado e o debounce dos filtros foram estabilizados sem remount da página. | `DeslocamentosPage.filtros.test.tsx`; falta cancelamento/latest-wins das requisições já disparadas. |
| `M15-10` | parcial | A Fase A envia `valor_unitario`/`ano_uso`, exibe erro por campo e torna `codigo_produto` read-only. | `buildCompraPayload.test.ts`; a issue e o desenho da Fase B continuam pendentes. |
| `M16-07` | parcial | O payload DAT normaliza DateFields e mapeia as datas AVALIAR para os campos plurais. | `buildDATRegistroPayload.test.ts`; a tela ainda reduz JSONFields multivalorados ao primeiro item e falta prova API→banco. |
| `M16-08` | resolvido | Choices, labels e payload de status passaram a coincidir com o contrato atual do backend. | `statusContract.test.tsx`; os enums ainda são duplicados manualmente. |
| `M17-02` | resolvido no caminho causador | A edição busca o endpoint de detalhe antes de preencher o formulário. | `editFetchesDetail.test.tsx`; não houve datafix para datas apagadas antes da correção. |
| `M19-01` | resolvido no runtime | `recalcular_ch()` agrega no banco, sem ler o prefetch obsoleto após o PATCH inline. | `test_plano_formacoes.py` cobre o primeiro PATCH e duas edições sequenciais; passivo antigo só se autocorrige na próxima edição. |
| `M03-10` | parcial | `Usuario.__str__` e o logging textual passaram por redação central de PII. | `AuditLog.details.username` ainda é persistido em tentativas de login. |
| `M05-05` | resolvido | O serviço transacional removeu o buffer global e registra a mudança de Grupo×Capability com ator e delta. | `test_audit_service.py` e `test_audit_privilege_sites.py`. |

Nesta passagem, executaram com **13/13 testes verdes** estes quatro arquivos frontend:
`DeslocamentosPage.filtros.test.tsx`, `buildDATRegistroPayload.test.ts`,
`statusContract.test.tsx` e `editFetchesDetail.test.tsx`. `buildCompraPayload.test.ts`, os
testes backend e a suíte Bats existem no `HEAD`, mas não foram reexecutados nesta passagem;
o backend permanece Docker-only.

## Plano de continuidade

### Onda V0 — tornar a fila atual novamente — **executada**

1. ~~Revalidar os 46 itens `aberto` contra `main 6d73ba29`~~ — feito em 2026-08-19 (`f6eecd5f`)
   e reconciliado de novo em 2026-08-25 contra `d8e64714`.
2. **Pendente.** Itens dependentes de ambiente (nginx/edge, DR, envs, dados) continuam sem
   observação read-only em produção. Código versionado não prova deploy, firewall, env ou dados.
3. **Pendente.** O residual do import de usuários que ainda altera cadastro/`is_active` de
   qualquer alvo não-superuser segue sem ID próprio; não reabrir o P0 de autoatribuição de
   grupos já fechado.
4. ~~Recalcular o total acionável~~ — 25 por código em 2026-08-25 (19 `aberto` + 6 `parcial`).
   O recorte P0/P1/P2 **não** foi refeito: severidade não foi tocada nesta passagem.

### Onda V1 — encerrar os parciais — **4 de 5 fechados**

1. ~~`M07-03`: AuditLog invariante para create/update/activate/deactivate~~ — `11219a7e` (#1736),
   2026-08-18. Helper `services/audit.py::auditar_privilege_flags` vira SSOT do before/after e o
   `save_model` do Django Admin passa a reusá-lo, então os dois caminhos não divergem mais.
2. ~~`M09-06`: abortar request anterior ou aplicar latest-wins~~ — `659c164f` (#1737), 2026-08-18.
   `seqRef` + `AbortController` em `DeslocamentosPage.tsx`, com teste de resposta fora de ordem.
3. **`M15-10` — único remanescente.** Concluir a Fase B ratificada para o domínio de Compras,
   sem reintroduzir campos sem dono ou contrato backend. Issue #1637 segue OPEN.
4. ~~`M16-07`: preservar JSONFields multivalorados~~ — `1fbcb34b` (#1744), 2026-08-18.
   Falta ainda a prova ponta a ponta formulário → API → banco → detalhe.
5. ~~`M03-10`: redigir `AuditLog.details.username` na escrita e na leitura~~ — `20c6f48d` (#1735),
   2026-08-18, com teste de CPF cru e formatado; épico #1657 CLOSED por `d2f226cc`.

Entram no lugar dos fechados cinco `parcial`, de duas procedências diferentes — a distinção
importa porque o veredito V0 não classificou os dois últimos como `parcial`:

- saíram `parcial` do próprio veredito V0 de 2026-08-19: `M15-02`, `M15-03` e `M23-02`. A tabela
  de reclassificados da V0 lista como `parcial` apenas `M12-19`, `M15-02`, `M15-03`, `M23-02` e
  `M05-03` — e `M12-19` e `M05-03` já fecharam;
- estavam entre os **39 LIVE** da V0 e só foram rebaixados a `parcial` na reconciliação de
  2026-08-25: `M14-01` (`2818a2ad` fechou apenas o ramo de vigência) e `M10-04` (`185fab4a`
  fechou apenas o shape do create).

Residuais em [Reconciliação de 2026-08-25](#reconciliação-de-2026-08-25-head-d8e64714).

### Onda V2 — corrigir por causa raiz

Tratar os épicos da tabela abaixo como unidades de desenho e teste, não como patches por tela.
Prioridade: autorização ator×alvo, integridade de import, perda silenciosa de dados, DR,
auditoria/PII, depois desempenho e limpeza. Cada PR deve citar os IDs fechados e os resíduos.

### Gates por correção

- teste RED que reproduz o mecanismo pelo entry point público; depois GREEN e não regressão;
- negativos de autorização/IDOR e revogação quando houver RBAC ou escopo de dados;
- backend somente em Docker; frontend no host; `rbac_lint` para mudança de autorização;
- `check_doc_links.py`, `check_doc_frontmatter.py` e atualização desta tabela no mesmo PR;
- staging gate completo antes de promover o PR; produção só recebe `em prod` após verificação.

## P0 históricos — detalhe e resolução

### M03-01 — rbac/imports: import de usuários permite auto-escalação a Gerente+Superintendência

- **Status atual:** resolvido no `main` por `ccbe1e05` em 2026-07-30; deploy não revalidado nesta passagem.
- **Status no corte de 2026-07-20:** vivo e alcançável por três contas DAT; issue #1610.
- **Correção atual:** `usuarios_import.py` exige ator superuser tanto na decisão quanto na primitiva de atribuição; a suíte adicionou casos negativos e positivos.

**Evidência histórica do defeito (2026-07-20)**

```text
Worktree C:\tmp\aprender_verify_main em d08acfa5 (HEAD da main).

1) Prova de execucao HTTP real (DRF APIClient, stack completa de middleware/URL/permissoes), DB isolado vm_m0301:
   docker exec -e DB_NAME=vm_m0301 aprender_vmain-web-1 pytest apps/core/tests/test_probe_m0301.py -q --no-migrations -p no:cacheprovider -s

   Cadeia: usuario `dat_attacker` (cpf 11144477735) apenas no grupo DAT -> POST /api/usuarios/import/?dry_run=false
   com CSV: `cpf,nome,grupos` / `11144477735,Dat Attacker,"Gerente,Superintendencia"`

   Saida observada:
     GRUPOS ANTES: ['DAT']
     HTTP STATUS: 200
     BODY: {'stats': {'created': 0, 'updated': 0, 'unchanged': 1, 'skipped': {'cpf_invalid': 0, 'nome_missing': 0, 'superuser_protected': 0, 'other': 0}}, 'pendencias': {...todas vazias...}, 'dry_run'
     GRUPOS DEPOIS: ['DAT', 'Gerente', 'Superintendencia']
     ESCALOU: True
     1 passed

   HTTP 200, zero pendencias, zero skips: o ator concedeu a si proprio Gerente + Superintendencia.

2) Prova de que a correcao nao existe em producao:
   git diff --stat 94f27651 HEAD -- v2/backend/apps/core/services/usuarios_import.py v2/backend/apps/core/views_import_usuarios.py
     -> saida VAZIA (arquivos byte-identicos entre prod 94f27651 e main d08acfa5)
   git log --oneline 94f27651..HEAD -- <mesmos arquivos>
     -> nenhum commit
   git log --oneline 90f6a048..HEAD -- v2/backend/apps/core/services/usuarios_import.py
     -> nenhum commit (inalterado desde o baseline da auditoria)

3) Busca por guard: grep "SuperuserOnly|allowlist|actor" nos dois arquivos retorna apenas
   views_import_usuarios.py:113, um comentario sobre allowlist de SUFIXO de arquivo (#1343, path-injection) — nada de RBAC.

Arquivo de probe removido; `git status --porcelain` nao lista test_probe_m0301.py.
```

### M26-01 — infra/DR: restore_db.sh roda `gzip -t` antes de decifrar e rejeita todo backup .age de producao

- **Status atual:** resolvido no `main` por `8f392636` em 2026-08-10; deploy e ensaio de DR real não revalidados nesta passagem.
- **Status no corte de 2026-07-20:** vivo em produção; issue #1611.
- **Ator real:** Nao depende de RBAC/grupo — o alcance e operacional. Qualquer operador/SRE com acesso a VM02_DB que execute a ferramenta oficial de restore durante um incidente. O censo de grupos e irrelevante aqui (Diretoria/Apoio de Coordenacao nao entram). Impacto potencial: 148 usuarios ativos, todo o banco de producao.

**Evidência histórica do defeito (2026-07-20)**

```text
HEAD do worktree = d08acfa5. `restore_db.sh:91` executa `gzip -t "$BACKUP_FILE"` incondicionalmente; o branch `.age` so aparece em `:113-119`. A paridade host/container foi conferida naquela execução; o digest original ficou truncado no registro e não é usado como evidência do HEAD atual.

Historico (arquivo v2/infra/scripts/restore_db.sh):
  git log --oneline 94f27651..HEAD -- <arq>  => VAZIO  (prod == main neste ponto; defeito VIVO em prod)
  git log --oneline 90f6a048..HEAD -- <arq>  => VAZIO  (nada mudou desde a auditoria)
  ultimo commit no arquivo: a7428bc8 (#1543) — corrigiu a SELECAO de .age (:36,:56,:61), nao a VERIFICACAO.

Prod grava exclusivamente .age: backup_db.sh:44-52 (fail-closed sem recipient; nome vira .sql.gz.age quando ha recipient) + docker-compose.prod.yml:197 (BACKUP_AGE_RECIPIENT=age1h52qdv3m...).

Probe isolado (container aprender_vmain-web-1, DB_NAME=rv_m26_01):
  head -c22 do artefato .age => "age-encryption.org/v1"
  gzip -t <.age>       => "gzip: ...: not in gzip format"  exit=1
  gzip -t <.sql.gz>    => exit=0   (controle)

End-to-end pela ferramenta oficial, TRES caminhos de entrada, todos abortam:
 (A) arquivo explicito:
     printf 'yes\n' | bash /app/infra/scripts/restore_db.sh /tmp/m26probe/backup_full_20260720_010000.sql.gz.age
     -> "[..] Verifying backup integrity... / gzip: ...: not in gzip format / ERROR: Backup file is corrupted!"  EXIT_CODE=1
 (B) --latest (dir com .sql.gz antigo + .age recente): mesma saida, mesmo abort.
 (C) interativo, selecao "1": mesma saida, mesmo abort.
Em nenhum caso passou da linha 91 — DROP DATABASE (linha 107) NUNCA alcancado (fail-closed, sem destruicao de dados).

Cobertura: zero. `find . -name "*.bats"` => apenas v2/infra/deployer/tests/{hooks_check_backup,integration,lib_gc,lib_guards,systemd_units}.bats. Nenhum teste referencia restore_db.

Achado adicional no mesmo corte: `restore_db.sh:17` hardcodava
`BACKUP_DIR="/var/backups/aprender"` e ignorava a variável de ambiente, ao contrário de
`backup_db.sh`. O commit `8f392636` também corrigiu esse ponto.

Nota operacional: `command -v age` no container web => MISSING. Mesmo apos corrigir a ordem, o restore precisa rodar onde o binario `age` exista — verificar host/imagem alvo.
[CORRIGIDO EM 2026-07-24 — ver "Retificacao" abaixo: o probe rodou num container de DEV. A imagem de PRODUCAO tem o binario `age` (Dockerfile.prod:56).]

Higiene: nenhum arquivo de probe criado no host; artefatos de container removidos (/tmp/m26probe e /var/backups/aprender). `git status --porcelain` mostra apenas test_probe_m1608.py e test_probe_m1702
```

#### Contexto

`v2/infra/scripts/restore_db.sh` executa `gzip -t "$BACKUP_FILE"` **incondicionalmente** na Step 1 (linha 91), antes do branch que trata artefatos cifrados com `age` (linhas 113-119).

Producao grava **exclusivamente** `backup_full_*.sql.gz.age`:
- `backup_db.sh:44-52` — fail-CLOSED: sem `BACKUP_AGE_RECIPIENT` e sem `BACKUP_ALLOW_PLAINTEXT=1` o backup aborta; com recipient o nome do arquivo vira `.sql.gz.age`.
- `v2/infra/docker-compose.prod.yml:197` — `BACKUP_AGE_RECIPIENT: age1h52qdv3m73yv75ussvuten7ckhkhr5axl3kgjnadl89j5ux265ls2jda8c` definido.

Um artefato `age` comeca com o cabecalho de texto `age-encryption.org/v1`, que nao e gzip. Logo `gzip -t` retorna 1 e o script aborta com **`ERROR: Backup file is corrupted!`** — mensagem factualmente falsa. Resultado: **o unico formato de backup que existe em producao nao pode ser restaurado pela ferramenta oficial de restore.**

Agravantes:
- A mensagem e ativamente enganosa. Sob pressao de incidente, um operador pode concluir que a cadeia inteira de backups esta corrompida e desistir do restore.
- Atinge os **tres** caminhos de entrada (arquivo explicito, `--latest`, modo interativo) — a selecao ja e ciente de `.age` (`:36,:56,:61`), so a verificacao nao e.
- Zero cobertura **a epoca do achado**: nao existia `.bats` para `restore_db.sh`. A suite foi **criada por `8f392636`** (2026-08-10, #1691 — o proprio fix de `M26-01`) com 5 casos, e **ampliada por `3bca74f3`** (2026-08-21, #1793) com os 2 de `M26-02`, somando os 7 de hoje. A ausencia de teste foi a causa de o defeito sobreviver — nao um sintoma remanescente. O que segue descoberto e o drill real (`M26-03`, #1646): os bats exercitam o script, nunca um `.age` restaurado num banco real.
- Bug secundario adjacente: `BACKUP_DIR` esta **hardcoded** em `restore_db.sh:17` (`/var/backups/aprender`) e nao respeita a env var, enquanto `backup_db.sh:31` usa `BACKUP_DIR="${BACKUP_DIR:-/backups}"`. Dentro do container (mount `/var/backups/aprender:/backups`) o `--latest` nao acha nada.

Atenuante: a falha e **fail-closed** — para na linha 91, ANTES do `DROP DATABASE` da linha 107. Nao ha destruicao de dados, e um operador experiente pode contornar manualmente com `age -d -i /etc/backup-key.txt <arq> | gunzip | psql`. O dano e RTO estourado + perda de confianca no DR, nao perda de dados.

#### Evidencia

Ambiente: worktree em `d08acfa5` (main), container `aprender_vmain-web-1`, `DB_NAME=rv_m26_01`.

Paridade host/container confirmada (`md5sum` = `34849168dbee9bb49c5c47212e838568` nos dois).

**O codigo nao mudou nem desde a auditoria nem em relacao a prod:**
```
$ git log --oneline 94f27651..HEAD -- v2/infra/scripts/restore_db.sh
(vazio)
$ git log --oneline 90f6a048..HEAD -- v2/infra/scripts/restore_db.sh
(vazio)
```
Ultimo commit a tocar o arquivo: `a7428bc8 fix(backup): fecha as camadas silenciosas do DR (fail-closed, pipefail, .age) (#1543)` — corrigiu a **selecao** de `.age` mas nao a **verificacao**.

**Probe isolado do `gzip -t`:**
```
== head do .age ==
age-encryption.org/v1
== gzip -t no .age ==
gzip: .../backup_full_20260720_010000.sql.gz.age: not in gzip format
exit=1
== gzip -t no controle .sql.gz ==
exit=0
```

**End-to-end pela ferramenta oficial, caminho de arquivo explicito:**
```
$ printf 'yes\n' | bash /app/infra/scripts/restore_db.sh /tmp/m26probe/backup_full_20260720_010000.sql.gz.age
Backup file: /tmp/m26probe/backup_full_20260720_010000.sql.gz.age
Database: rv_m26_01
[Mon Jul 20 16:38:11 UTC 2026] Starting restore...
[Mon Jul 20 16:38:11 UTC 2026] Verifying backup integrity...
gzip: /tmp/m26probe/backup_full_20260720_010000.sql.gz.age: not in gzip format
ERROR: Backup file is corrupted!
EXIT_CODE=1
```

**`--latest` (diretorio com `.sql.gz` antigo + `.age` recente):**
```
[..] Verifying backup integrity...
gzip: /var/backups/aprender/backup_full_20260720_010000.sql.gz.age: not in gzip format
ERROR: Backup file is corrupted!
```

**Modo interativo, selecao "1" (mais recente):**
```
[..] Verifying backup integrity...
gzip: /var/backups/aprender/backup_full_20260720_010000.sql.gz.age: not in gzip format
ERROR: Backup file is corrupted!
```

Em nenhum caso a execucao passou da linha 91 — o `DROP DATABASE` (linha 107) nunca foi alcancado.

#### Correção implementada

O commit `8f392636` tornou a verificação ciente do formato: para `.age`, valida o binário e a
chave, decifra e então executa `gzip -t` dentro de subshell com `pipefail`; para `.sql.gz`,
mantém a verificação direta. O mesmo commit fez `BACKUP_DIR` respeitar a variável de ambiente.

O `pipefail` é local de propósito. Torná-lo global quebraria a seleção `ls A B | head` quando
produção contém apenas `.age` e o glob de `.sql.gz` não casa. A imagem de produção instala
`age` (`v2/infra/Dockerfile.prod`); a imagem de desenvolvimento não.

#### Retificacao de 2026-07-24 — o probe do `age` mediu o ambiente errado

O probe original (`command -v age` no container `aprender_vmain-web-1`) rodou sobre a imagem de
**desenvolvimento**, e a conclusao "a imagem web nao tem `age`" foi generalizada para producao.

Evidencia contraria: `v2/infra/Dockerfile.prod:47-57` instala explicitamente `age` na camada de
runtime, com o comentario *"cifra os dumps de DB em repouso (backup_db.sh + BACKUP_AGE_RECIPIENT;
#1455). O recipient (chave publica) ja esta no Env de prod, mas o binario faltava"* — ou seja, a
ausencia foi um bug **ja corrigido**. `v2/infra/Dockerfile.dev` nao instala `age`.

Consequencia pratica: o contorno manual `age -d -i <chave> <arq> | gunzip | psql` **roda** no
worker de produção. No corte de 2026-07-24, o `M26-01` ainda era **P0 e vivo** — o defeito
era a ordem das operações, não a falta do binário. O código foi corrigido depois por
`8f392636`; deploy e drill operacional atuais não foram revalidados aqui.

Mesma classe de erro que o `M27-05` (porta 8000): conclusao tirada de um ponto de observacao que
nao era o ambiente sob analise.

#### Testes de regressão implementados

`v2/infra/scripts/tests/restore_db.bats` fornece a primeira cobertura do script:

1. `restore .age passa na verificacao de integridade` — gerar `.sql.gz` valido, cifrar com `age -r`, invocar o script com stubs de `psql` no PATH, assertar que a saida contem `Backup integrity OK` e **nao** contem `Backup file is corrupted`.
2. `restore .age realmente corrompido falha` — truncar o corpo cifrado; assertar exit != 0 e que nenhum `DROP DATABASE` foi emitido ao stub de `psql`.
3. `restore .sql.gz simples continua funcionando` (nao-regressao).
4. `BACKUP_DIR respeita a env var` — `--latest` com `BACKUP_DIR` apontando para tmpdir seleciona o artefato de la.
5. `--latest` funciona quando o diretório contém somente `.age`.

#### Verificação restante

- A suíte `v2/infra/scripts/tests/restore_db.bats` integra o workflow de staging e cresceu
  depois: `3bca74f3` (#1793, 2026-08-21) somou os cenários de `M26-02` aos cinco originais. Não
  foi reexecutada em 2026-08-19 nem em 2026-08-25 porque Bats não está instalado no ambiente
  local — a contagem corrente sai do arquivo, não daqui.
- Ensaio de DR real em staging: `backup_db.sh` com `BACKUP_AGE_RECIPIENT` -> gera `.age` -> `restore_db.sh --latest` -> restaura -> conferir `TABLE_COUNT` e contagem de linhas de tabelas-chave (`core_usuario`, `core_solicitacao`) contra a origem.
- Registrar a data do ensaio em `v2/docs/DISASTER_RECOVERY.md` / `BACKUP_OPERATIONS.md`.

#### Risco de rollout

Baixo. A mudança atingiu apenas o script de operação manual, sem migration. O comportamento
para `.sql.gz` simples foi preservado. O risco residual é operacional: sem drill real, ainda
não há prova de RTO nem de restauração ponta a ponta com a chave e o PostgreSQL de staging.

## Causas raiz (épicos)

Achados que compartilham uma causa raiz devem ser corrigidos estruturalmente, não com N
patches pontuais.

Estado no corte de 2026-08-25 (`d8e64714`). `Issue` traz o estado no GitHub; `Status` traz o
estado **do código**. Os dois divergem de propósito: #1664 segue OPEN com os dois achados
fechados no código, e #1657 está CLOSED com resíduo teórico registrado em `M23-02`.

| Causa raiz | Sev. | Achados | Issue | Status (código) |
|---|---|---|---|---|
| paginacao-global-sem-page-size | P1 | `M01-07`, `M18-06` | #1653 CLOSED | resolvido (`aa8bfb5c`, `062df0ec`; 2026-08-20) |
| list-serializer-como-fonte-de-detalhe | P1 | `M15-09`, `M17-02`, `M18-05` | #1654 OPEN | parcial (`M15-09` e `M18-05` abertos) |
| contrato-fe-be-sem-ssot | P1 | `M15-10`, `M16-07`, `M16-08`, `M09-05`, `M05-07` | #1655 OPEN | parcial (`M16-07`/`M16-08` fechados; `M15-10` parcial; `M09-05`/`M05-07` abertos) |
| escopo-ator-alvo-ausente | P0 | `M22-01` (duplicata histórica de `M03-01`), `M07-02`, `M10-01`, `M10-04`, `M14-01` | #1656 OPEN | parcial (`M10-04` e `M14-01` seguem: `M10-04` sem policy ator×alvo por participante; `M14-01` só no ramo sem `gerencia_id`) |
| auditoria-nao-invariante-e-pii | P1 | `M07-03`, `M05-05`, `M23-02`, `M03-10` | #1657 CLOSED | parcial (`11219a7e`, `20c6f48d`, `d2f226cc`, todos 2026-08-18, fecham `M07-03`/`M05-05`/`M03-10`; `M23-02` segue `parcial` na fila, com o resíduo teórico) |
| resolvers-por-rotulo-humano | P1 | `M02-09`, `M04-01`, `M22-14`, `M15-05` | #1658 OPEN | parcial (`M02-09`/#1613 resolvido: `resolve_projeto`/`resolve_tipo_evento` rejeitam ambiguidade + norm simétrica no import DAT; `M04-01`/`M22-14`/`M15-05` seguem abertos) |
| import-bypassa-invariantes | P1 | `M08-12`, `M10-07`, `M17-01`, `M15-04` | #1659 OPEN | aberto (nenhum dos 4 tem fix) |
| chave-de-seguranca-nao-canonica | P1 | `M03-03`, `M01-01` | #1660 CLOSED | resolvido (`9ae753e6` 2026-08-18, `d24da3df` 2026-08-20) |
| nginx-add-header-heranca | P2 | `M06-04`, `M27-24` | #1661 CLOSED | resolvido (`88626736`, 2026-08-19) |
| dr-restore-nao-exercitado | P0 | `M26-01`, `M26-02`, `M26-03` | #1662 OPEN | parcial (`M26-01`/`M26-02` fechados; `M26-03` aberto e o drill real de DR nunca ocorreu) |
| grade-mensal-agregacao-e-populacao | P1 | `M14-02`, `M14-03`, `M14-05` | #1663 OPEN | parcial (`4321d90b`, `4f63caf0`; `M14-05` aberto) |
| motor-disponibilidade-sem-ssot-de-regra | P2 | `M08-07`, `M08-09` | #1664 OPEN | resolvido no código (`cd60882a`, `a986a250`; 2026-08-21) — issue segue OPEN |
| compras-sem-invariantes-nem-identidade | P1 | `M15-02`, `M15-03`, `M15-08` | #1665 OPEN | parcial (`M15-02`/`M15-03` parciais; `M15-08` aberto) |
| solicitacao-participantes-sem-ssot | P1 | `M10-05`, `M10-06` | #1666 OPEN | aberto (o fix de `M10-04` declara a reconciliação do update fora de escopo) |
| estado-derivado-obsoleto-apos-escrita | P2 | `M05-03`, `M19-01` | #1667 CLOSED | resolvido (`f9e40902` 2026-08-11, `01ddb4cd` 2026-08-21) |
| frontend-ciclo-de-requisicoes | P1 | `M09-06`, `M12-19` | #1668 CLOSED | resolvido (`659c164f` 2026-08-18, `3ab590d6` 2026-08-20) |

## Já corrigidos — não abrir issue

Registrados para memória: foram apontados pela auditoria e **já estavam resolvidos** quando
o relatório foi lido. É a prova de que uma auditoria longa envelhece e precisa ser revalidada
contra `HEAD` antes de virar fila de trabalho.

| ID | Situação | O que fechou |
|---|---|---|
| `M05-01` | corrigido em prod | v2/backend/apps/core/views/admin.py:494-500 — `GroupViewSet.get_permissions()`: list/retrieve → `HasPerm("manage_purchases_and_materials")`, TODO o resto (creat… |
| `M05-02` | corrigido em prod | C:\tmp\aprender_verify_main\v2\backend\apps\core\views\admin.py:492-499 — GroupViewSet.get_permissions() devolve [SuperuserOnly()] para toda action que nao seja… |
| `M02-10` | corrigido em prod | v2/frontend/public/sw.js:161 — `if (pathname.startsWith('/api/me/')) return false;` dentro de `isCacheableApiRoute()`. Não é um guard HTTP (não devolve status):… |
| `M06-03` | corrigido so na main | C:\tmp\aprender_verify_main\v2\frontend\eslint.config.js:38 — bloco com files: ['src/**/*.{ts,tsx}'] + tseslint.configs.recommended. Nao e guard HTTP (achado de… |

`M22-01` foi removido da lista acionável por ser **duplicata de `M03-01`** — mesmo defeito,
contado duas vezes no relatório original.

## Premissas de ambiente — snapshot confirmado pelo dono em 2026-07-20

Fatos observados diretamente em produção. Substituem qualquer inferência feita a partir
do repositório, de `.env.production.example` ou do ambiente de desenvolvimento.

#### F2 — SHA em produção ✅

- Produção: `v2026.07.18-94f2765` (`94f27651`)
- Baseline da auditoria: `90f6a048` (**23 commits atrás**)
- `main` em 2026-07-20: `d08acfa5` (**33 commits à frente da baseline**)

Consequência: 3 de 12 achados reverificados já estavam corrigidos (25%). `M05-01` e
`M05-02` fechados em produção pelo `82dfa0f2` (#1567).

#### F3 — Censo de grupos ✅

Membros **ativos, não-superuser**, em produção:

| Grupo | Ativos |
|---|---:|
| Formador | 94 |
| Coordenador | 42 |
| Gerente | 9 |
| DAT | 3 |
| Controle | 1 |
| Superintendência | 1 |
| Assistente Administrativo | 1 |
| Diretoria | **0** |
| Apoio de Coordenação | **0** |

Total de usuários ativos: 148. **Superusers ativos: 1.**

Consequências:
- No snapshot anterior à correção, `M03-01` era alcançável por três contas DAT. O mecanismo
  de autoescalação foi corrigido por `ccbe1e05`; o censo atual não foi refeito.
- Achados alcançáveis apenas por Diretoria ou Apoio de Coordenação **não têm ator hoje**.
- **Bus factor de 1 superuser.** Agravado pelo #1567, que tornou a administração de
  Grupo×Capability superuser-only. Se essa conta cair, ninguém administra RBAC.
  A auditoria já tinha isso como decisão pendente em M05 (superuser primário + backup).

#### F4 — Google Calendar ✅ ATIVO

- `GCAL_AUTH_MODE = oauth`
- `GCAL_CLIENT = google` (cliente real, **não** stub)
- `GCAL_ALLOWED_DOMAIN = aprendereditora.com.br`
- `GCAL_OAUTH_CLIENT_ID` preenchido (72 chars)
- `GCAL_OAUTH_CLIENT_SECRET` preenchido (35 chars)
- `GCAL_ENCRYPTION_KEY` preenchido (44 chars — tamanho de chave Fernet)
- `GCAL_OAUTH_REDIRECT_URI` preenchido (57 chars)
- `GCAL_CALENDAR_ID` preenchido (7 chars — compatível com `primary`)
- `GCAL_SERVICE_ACCOUNT_JSON` **não existe**

Consequência: os 13 achados de M12 que dependiam de OAuth ativo têm a premissa
**confirmada** — não são teóricos e **nenhum** é despriorizado. Destaque para `M12-15`
(state de OAuth de um usuário aceito no callback de outro) e para o uso do
`GCAL_CALENDAR_ID` global no cancelamento em vez do calendário do operador.

> Nota de 2026-08-25: `M12-15` foi fechado no código por `9328227f` (#1760, 2026-08-19) — o
> ownership do state passou a viver no cache e o callback ganhou `CanUseGcal`. O snapshot de
> ambiente acima continua sendo o de 2026-07-20; a premissa (OAuth por usuário, sem service
> account) não foi remedida.

#### F1 — Porta 8000 ✅ (parcial)

O dono testou por **4G, fora da rede corporativa**: a porta **não responde**. A porta
está protegida por allowlist de firewall externo (Golden).

Refuta o achado `M27-05` como "exposição pública" — os probes anteriores rodaram de
dentro da rede allowlisted e concluíram além do que o ponto de observação sustentava.

O que **permanece** verdadeiro (reconferido em 2026-08-25, `d8e64714`):
`v2/infra/docker-compose.prod.yml:101` ainda publica `"${BACKEND_HOST_PORT:-8000}:8000"`, sem
bind em `127.0.0.1`, então o firewall externo é a **única** camada protegendo um
canal em texto claro que serve a API e o `/admin` do Django, fora do TLS e do `limit_req`.
Reclassificado P0 → **P2**, defesa em profundidade. Correção que preserva o consumidor
legítimo (`deployer/apply.sh:73-80` usa `confirm_localhost`):
`127.0.0.1:${BACKEND_HOST_PORT}:8000`.

#### Ainda não verificado

- **F5** — conteúdo real dos envs no Portainer, comparado 1-a-1 com o template. 18 achados
  dependem disso, e é o único fato com potencial de **promover** algo a P0 (ex.: `DEBUG=True`).
- **F7** — o beat roda e existe hoje backup restaurável? O código de `M26-01` e o de `M26-02`
  foram corrigidos (`8f392636`, `3bca74f3`), mas sem drill real o risco operacional de DR
  continua aberto junto de `M26-03`, que é justamente o ID do teste que nunca exercitou o
  round-trip cifrado. Precedente relevante: #1537, backup que nunca rodou.
- **F1 (resto)** — configuração do edge real. O Nginx Proxy Manager é **externo ao
  repositório** (`docker-compose.prod.yml:329-339`); se ele **anexa** `X-Forwarded-For` em
  vez de sobrescrever, `M01-01` e `M03-03` sobem para P1 (bypass remoto de lockout/throttle).
  **Atualizado em 2026-08-25:** os dois foram fechados no código — `9ae753e6` canonicaliza a
  chave de lockout/throttle e `d24da3df` faz `get_client_ip` contar `NUM_PROXIES` saltos a
  partir da **direita**, ignorando entrada forjada à esquerda. A pergunta sobre o edge deixa
  de ser condição de severidade e vira verificação de topologia: `NUM_PROXIES=2` assume
  `NPM → nginx frontend → gunicorn`, e um salto a mais ou a menos no edge real reabre o
  bypass. Continua **não verificado** em produção.
- **F6** — homônimos e duplicatas nos dados reais (`M02-09`, `M22-14`): dano atual ou preventivo?

---

## Por que este documento existe separado

O erro mais caro da auditoria não foi um achado errado — foi um achado **certo no mecanismo e
errado na consequência**, sustentado por uma premissa de ambiente que ninguém tinha medido.
O caso exemplar foi o `M27-05`: dois agentes concluíram "porta 8000 aberta na internet" a
partir de probes rodados de dentro da rede allowlisted. O dono refutou testando pelo 4G.

A lição vale para qualquer auditoria futura deste sistema:

- Confirmação por um segundo observador **do mesmo ponto de observação** não é independência.
- Premissa de ambiente não medida erra nos **dois** sentidos: inflou o `M27-05`, e teria
  deflacionado os 13 achados de GCal se alguém tivesse assumido stub por conveniência.
- Auditoria sobre codebase que recebe ~30 commits/mês nasce envelhecendo. Fixe o SHA no
  cabeçalho e revalide contra `HEAD` antes de publicar.
