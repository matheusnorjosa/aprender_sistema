---
title: Plano — Import da planilha + features derivadas
status: draft
last_verified: 2026-08-26
owner: backend
related:
  - ../specs/backend/imports.spec.md
  - ../specs/backend/dat.spec.md
  - ../specs/backend/rbac.spec.md
  - ../specs/domain/politica-aprovacao.spec.md
---

# Plano — Import da planilha → sistema + features derivadas

## Contexto (por quê)

O `aprender_sistema` vai substituir as planilhas. O dado limpo (pessoas, projetos,
setores, vínculos, compras, eventos) já existe do lado do `sheets.banco` (contrato v14,
snapshot 2026-08-21) e entra por **import** — não por raspagem (os scripts de raspagem
estão aposentados, DECIDIDO 25/08). Este plano cobre tudo que o **lado-sistema** precisa
fazer para consumir esse contrato e as features que saem dele.

Autoridade e detalhe: `ESPELHO_SISTEMA_PLANILHA.md` (o que o sistema faz, em `v2/docs/`) +
`REFERENCIA-DOMINIO.md` (o que a planilha contém, no `sheets.banco`).

> **Caminho crítico:** o `sheets.banco` emite a **v15** (com `setor_canonico`, `segmento_norm`,
> `external_event_id`, correções §9.2). As migrations/import de verdade dependem dela.
> **RF01 imutável:** não importar dado real até um dry-run do `--apply` passar verde +
> autorização do dono.

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

- [ ] **B.1** `Gerencia.setor_canonico` (CharField) — recebe o de-para do sheets.banco.
- [ ] **B.2** Setor do projeto: popular `projeto.gerencia` via import (hoje 124/125 vazio). Decidir
      se `projeto.setor` vira campo próprio ou fica derivado de `gerencia__setor_canonico`.
- [ ] **B.3** `projeto.projeto_geral` (hoje 125/125 vazio) — a regra de códigos mora na família.
- [ ] **B.4** Papel `SUPORTE`/`OPERACIONAL` no enum de `EquipeGerencia.papel` (ou mapeamento
      explícito) — sem promover a APOIO.
- [ ] **B.5** `Usuario.desativado_localmente` (BooleanField) — estado local que o import não
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
```

## Riscos / o que NÃO fazer

| risco | mitigação |
|---|---|
| import reativa desligado (Elienai) | `desativado_localmente` (B.5) vence a fonte; import nunca reativa |
| comparar setor por igualdade barra 46% | usar `setor_canonico` dos dois lados (B.1) |
| transferência duplica evento no GCal | eventId determinístico → UPDATE; editar solicitação existente, não criar nova |
| import cego sobrescreve data-fix manual | dry-run verde + autorização (RF01); create-only + never-overwrite |
| migration para contrato que ainda muda | migrations (B) só depois da v15 |
| apagar model "morto" que é vivo | seguir a §9.1 re-verificada do espelho (🔴 NÃO AGIR) |

## Requests ao `sheets.banco`

**Emitir na v15:** `equipe_gerencia.setor_canonico` (de-para aplicado) · `projeto→projeto_geral`
o mais completo possível (regra de códigos) · `segmento_norm` + `external_event_id` (identidade
de evento, evita colisão de hash) · corrigir `prova.csv` (0 linhas) · decisão sobre `colecao` ·
dropar os 6 artefatos internos.

**Dados/respostas:** lista dos 34 eventos futuros do Elienai (município/data/status publicação) —
p/ desenhar a transferência (F.1) · quem atende os 21 projetos órfãos (A COR DA GENTE, ED
FINANCEIRA, SOU DA PAZ, TRÂNSITO LEGAL) · reconcile 125×114 (mando minha lista, ele aponta os 11) ·
`nome_curto` armazenado no `usuario.csv` · confirmar que não há sinal de desativação na fonte
(Elienai fica em ATIVOS) → 100% gerido localmente.

## Aberto — dono

D6c (convite por e-mail interno) · quem atende os 4 setores órfãos · desenho da parte 3 da
transferência (assume-se re-publicação automática via GCal) · higiene do `usuario.csv` (CPF
duplicado/ausente, mod-11, cadastro sem cargo).
