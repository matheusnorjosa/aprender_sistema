---
status: active
last_verified: 2026-08-11
owner: matheusnorjosa
tipo: plano-de-programa
resumo: >
  Programa para corrigir a família de imports que gravam em tabelas legacy que
  nenhuma tela operacional lê (dado "some" da UI mesmo importado), + posse dos
  campos de compra (fronteira Controle x DAT). Fundamentado em 4 investigações
  de código (agentes) e nas decisões do dono.
sources_of_truth:
  - v2/backend/apps/core/models/ (Compra, DATCompra, Produto, Colecao, AcaoDAT, AcaoControle, DATAcao, DATCadastro, EquipeGerencia, Gerencia)
  - v2/backend/apps/core/services/ (controle_imports, controle_acoes_import, dat_cadastros_import, colecoes_import, produtos_import, export_contract_importer)
  - v2/frontend/src/pages/DAT/ImportacoesPage.tsx
  - v2/frontend/src/api/ops.ts (clientes homônimos / dead code)
  - v2/docs/specs/backend/dat.spec.md
---

# Plano — imports órfãos → telas operacionais (DAT) + posse dos dados de compra

> **Referência viva do programa.** Nasceu da issue #1640 e do #1637 (Parte B);
> a investigação revelou um padrão sistêmico, não casos isolados. Atacar por onda.

## 1. Descoberta central

Vários imports gravam numa tabela **legacy** enquanto a tela operacional lê **outra**
tabela. O mecanismo que mascara o vazamento: `ops.ts` mantém funções **homônimas**
(`listAcoes`/`listCompras`/`listCadastros`) apontando para endpoints legacy; só
`listCompras` tem consumidor vivo — `listAcoes` e `listCadastros` são **dead code**.
As telas roteadas usam os clientes de `datModule.ts` (operacionais). Nenhum modelo
legacy está marcado `deprecated` no código (o header de `models/workflow.py:2-4` ainda
os chama de "operacional"), então o vazamento é silencioso.

### Auditoria dos 11 cards de import

| Card | Grava em | Tela lê? | Destino operacional | Situação |
|---|---|---|---|---|
| Usuários | `Usuario` | sim | admin/lookup/options | saudável |
| Municípios | `Municipio` | sim | adminDAT/lookup | saudável |
| Produtos | `Produto` | sim | datModule/adminDAT | saudável |
| Eventos | `Solicitacao`+`Participation` | sim | calendário/aprovações | saudável |
| Bloqueios | `AvailabilityBlock` | sim | grade mensal | saudável |
| Deslocamentos | `Deslocamento` | sim | deslocamentos | saudável |
| Vínculos → `Gerencia` | `Gerencia` | sim | `/gerencias/` | saudável |
| **Vínculos → `EquipeGerencia`** | `EquipeGerencia` | não (tela) | — (RBAC usa em runtime) | **órfão de exibição** |
| **Ações** | `AcaoControle` | **não** | `DATAcao` (AcoesPage) | **ÓRFÃO** |
| **Cadastros DAT** (#1640) | `AcaoDAT` | **não** | `DATCadastro` (CadastrosPage) | **ÓRFÃO** |
| **Coleções** | `Colecao` | **não** | via `Produto.colecao` | **wiring incompleto** |
| **Compras** (#1637) | `Compra` | Controle sim / DAT não | split `Compra`↔`DATCompra` | **split-brain** |

## 2. Decisões do dono (registradas)

1. **Nenhum import foi pensado para ser histórico** — todos deveriam aparecer organizados
   nas telas operacionais.
2. **Ninguém está usando o sistema em produção ainda** → sem dado real em risco; as tabelas
   legacy têm só seed/teste. **Sem backfill cerimonioso**; pode-se **redirecionar + apagar**.
   (Corolário: o "vivo em produção, ator real todo dia" das issues era exagero de consequência
   do auditor; os fixes seguem válidos, a urgência era inflada.)
3. **Compras (#1637):** fornecedor / nº nota fiscal / data de entrega são **do CONTROLE**
   (que insere a compra, manual ou import); **o DAT nunca digita** — só visualiza. A planilha
   do Controle pode ainda não ter esses campos, mas pode passar a ter.
4. **Coleções:** é para ser usado → **WIRE** (ligar), não limpar.
5. **Legacy morto:** se é código morto, **limpar** (não congelar). Ordem importa (ver §4).

## 3. Fronteira de domínio (imutável no plano)

O código já tem uma fronteira **Controle x DAT** explícita e **testada**
(`v2/backend/apps/core/tests/test_compras_domain_boundary.py`): usuário DAT recebe **403**
em `/api/controle/compras/`; o Controle expõe `Compra` sem `valor`; o DAT expõe `DATCompra`
com `valor_unitario`. É o padrão `AcaoControle → DATAcao` ("Controle insere, DAT visualiza").
**Todo item deste plano respeita essa fronteira.**

## 4. Regra de ordem para "limpar" o legacy

Legacy que ainda é DESTINO de import **não** pode ser deletado antes de redirecionar:
1. redireciona o import para a tabela operacional (`DATAcao`/`DATCadastro`);
2. só então o legacy fica sem escritor e sem leitor → **deleta** (migration dropa a tabela +
   remove modelo/serializer/endpoint + o dead code homônimo em `ops.ts`).

Dead code puro (as funções `ops.listAcoes`/`listCadastros`, zero importadores) pode ser
deletado já, independente do redirect.

## 5. Programa por ondas

### Onda 0 — parar de sangrar + honestidade (rápido, baixo risco)
- **#1637 Fase A** (depende de #1714 mergear — mesmo arquivo):
  - `codigo_produto` vira mirror **read-only** no serializer (`source="produto.codigo"`;
    `serializers/dat_module/dat_compra.py`).
  - Remover do modal DAT os 3 inputs de procurement — `fornecedor`, `numero_nota_fiscal`,
    `data_entrega` (`ComprasPage.tsx`) + tirar `data_entrega` do `buildCompraPayload`.
  - Sem migration.
- **Deletar dead code homônimo** `ops.listAcoes`/`ops.listCadastros` (`api/ops.ts`).
- **Marcar `AcaoDAT`/`AcaoControle` como legacy** no header/docstring (hoje mentem "operacional").

### Onda 1 — órfãos de mapeamento fácil
- **Ações → `DATAcao`** — ✅ **FEITO** (PR #1759 redirect + PR do drop):
  `controle_acoes_import.py` grava em `DATAcao` (StatusEtapa derivado da data por etapa;
  upsert pela chave natural `(municipio, projeto)`; coordenador→`DATCoordenador` email→nome→null;
  `created_by`=request.user). **Correção ao plano:** NÃO há remap `Projeto`→`ProjetoGeral` aqui
  (ambos usam `Projeto`; o `ProjetoGeral` é da Onda 2/`DATCadastro`). `AcaoControle` **apagado**
  (migration `0085_drop_acao_controle`) + endpoint `/controle/acoes/` + serializer + admin
  removidos. (`ops.listAcoes` já não existia — Onda 0.)
- **Vínculos → tela read-only de `EquipeGerencia`** (o dado já move o RBAC — scoping em
  `views_availability.py`, `rbac/permissions.py`; só falta serializer/viewset/list + tela). — pendente.

### Onda 2 — órfãos difíceis / com desenho
- **Cadastros DAT → `DATCadastro`** (#1640): `AcaoDAT` é **evento** (1 por
  `municipio·projeto·tipo_acao·responsavel`), `DATCadastro` é **snapshot** (1 por
  `município·projeto_geral·plataforma`, colunas `status_*` por etapa). Exige **pivot
  linha→coluna** + remap de FK. Regras: derivar `plataforma` de `tipo_acao` (só prefixos
  "FORMAR-*"; sem plataforma → **rejeita com motivo**, não silencia); `projeto→projeto_geral`
  via `Projeto.projeto_geral` (quando `None` → rejeita a linha); upsert por chave natural;
  `created_by` = usuário-serviço; idempotência via `external_hash`. Depois **apagar `AcaoDAT`**.
- **Coleções → WIRE** (veredito: wiring incompleto — os leitores JÁ existem):
  - O ComprasDashboard **já tem** os cards "Coleções ativas" (`dat_module.py:497`,
    `ComprasDashboardPage.tsx:571`) e "Quantidade por Coleção" (`dat_module.py:500-515`,
    `ComprasDashboardPage.tsx:638-645`) — mas mostram **sempre 0 / "Sem coleção"** porque a
    FK `Produto.colecao` **nunca é populada** (produtos_import não seta; export-contract pula
    `colecao`; `ProdutoSerializer` nem tem o campo).
  - Fix: popular `Produto.colecao` no **import de produtos** (`produtos_import.py`: colher a
    coluna de coleção + `Colecao.objects.get_or_create(nome, projeto)` + setar a FK no create e
    no update); expor `colecao_nome` no `ProdutoSerializer` (`serializers/organizacao.py`);
    `colecao` no `filterset_fields` (`views/admin.py:260`); coluna/filtro na ProdutosPage +
    `/options/colecoes/`. **O dashboard não muda — os 2 cards acendem sozinhos.** O card de
    import "Coleções" avulso vira redundante (fundir no import de produtos ou virar editor de
    metadado).

### Onda 3 — #1637 Fase B (Compras Controle→DAT read-only)
- Quando o Controle passar a registrar fornecedor/NF/data_entrega: migration em **`Compra`**
  (não `DATCompra`) — `fornecedor` (texto ou entidade — decidir), `numero_nota_fiscal`
  (indexed, **não** `UNIQUE` simples: 1 NF cobre vários itens; unicidade real seria
  `(fornecedor,série,número)`), `data_entrega` (DateField null; **não** conflatar com
  `Compra.data` nem `DATCompra.data_compra`). Estender `controle_imports.py`. A **ComprasPage
  do DAT passa a exibir a `Compra` do Controle read-only** — resolve o split-brain.

## 6. Disciplina (todas as ondas)

- CP-04 (Entender→Planejar→Implementar→Testar) + TDD (RED antes de GREEN).
- Redirect de import: dry-run classify antes; `--apply` com allowlist.
- Sem backfill cerimonioso (não há usuários) — mas confirmar contagem das tabelas legacy antes
  de dropar; se houver dado real inesperado, subir para a disciplina de datafix
  (preflight→dry→apply, snapshot+postcheck).
- Atualizar `v2/docs/specs/backend/dat.spec.md` a cada redirect/apagamento.
- Não rodar dois redirects/migrations DAT juntos.
- **Regra do projeto:** não importar dado real sem autorização explícita do dono.

## 7. Decisões ainda em aberto

- Coleções: manter o card de import "Coleções" avulso, ou fundir no import de produtos? (§5 Onda 2)
- #1637 Fase B: `fornecedor` é entidade (normalizada) ou texto-livre?
- Ordem de execução das ondas / qual órfão dói mais primeiro.

## 8. Sequência imediata

1. Dono merga **#1713** (#1641) + **#1714** (#1637 Fase A base).
2. Agente sela **#1637 Fase A** (rápido, sem migration).
3. Programa segue onda por onda, cada uma com seu PR (+ gate) e atualização de spec.
