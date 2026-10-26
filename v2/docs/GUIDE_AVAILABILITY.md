# Guia: Disponibilidade Multi-Setor

Este guia documenta a funcionalidade de visualização de disponibilidade por setor.

## Visão Geral

A funcionalidade de disponibilidade permite visualizar a grade mensal de formadores/coordenadores e seus bloqueios de disponibilidade. Com o suporte multi-setor, coordenadores e gerentes de outros setores (Vidas, Fluir, ACerta, etc.) podem visualizar a grade do seu próprio setor.

## API

### GET /api/availability/monthly

Retorna a grade mensal de disponibilidade.

**Query Parameters:**

| Parâmetro | Tipo | Obrigatório | Descrição |
|-----------|------|-------------|-----------|
| `year` | int | Sim | Ano (YYYY) |
| `month` | int | Sim | Mês (1-12) |
| `role` | string | Sim | "FORMADOR" ou "COORDENADOR" |
| `gerencia_id` | int | Não | ID da gerência. **Se omitido, o escopo vem do usuário** — ver abaixo |
| `sector` | string | Não | Filtro por nome do projeto |
| `q` | string | Não | Filtro por nome do formador; o e-mail só entra se o termo não tem dígito (pode levar o CPF) |

> 🔴 **Corrigido em 2026-07-24.** Este guia dizia que omitir `gerencia_id` "assume
> SUPERINTENDENCIA (SUPER)". **Falso.** Em `MonthlyAvailabilityView.get` (`apps/core/views_availability_monthly.py`),
> quando `gerencia_id is None`:
>
> - quem tem a capability `view_all_availability` recebe escopo **amplo** (`has_wide_scope`,
>   `cache_scope="wide"`);
> - os demais são escopados aos usuários das **próprias** gerências via `EquipeGerencia`
>   (`EquipeGerencia.gerencias_de_atuacao`, no `else` do mesmo ramo);
> - quem não tem papel G/C/A vigente em gerência ativa recebe **403** antes de chegar à view
>   (`HasSectorAccess`); o ramo "só o próprio usuário" da view não é alcançado (ver "Permissões").
>
> `build_monthly_grid` é então chamado com `gerencia_id=None` **+ `allowed_user_ids`** (mais abaixo, no mesmo `MonthlyAvailabilityView.get`).

**Exemplos:**

```bash
# Escopo derivado do usuário (amplo ou das próprias gerências; sem vínculo G/C/A = 403)
GET /api/availability/monthly?year=2026&month=1&role=FORMADOR

# Grade do setor Vidas (gerencia_id=2)
GET /api/availability/monthly?year=2026&month=1&role=FORMADOR&gerencia_id=2

# Grade filtrada por projeto
GET /api/availability/monthly?year=2026&month=1&role=FORMADOR&gerencia_id=2&sector=VIDA%20E%20CIÊNCIAS
```

**Resposta:**

```json
{
  "days": [1, 2, 3, ..., 31],
  "legend": {
    "E": "1 evento",
    "2": "≥2 eventos",
    "P": "Bloqueio parcial",
    "T": "Bloqueio total",
    "X": "Evento + bloqueio",
    "D": "Deslocamento",
    "D1": "Evento + deslocamento"
  },
  "people": [
    {
      "id": 123,
      "name": "João Silva",
      "email": "joao@example.com",
      "ch_month": 40.5,
      "ch_year": 320.0,
      "position_month": 1
    }
  ],
  "cells": [["E", "", "2", ...], ...],
  "details_index": {
    "0:2": [{"id": 456, "municipio": "Fortaleza", ...}]
  }
}
```

### GET /api/availability-blocks/

Retorna os bloqueios de disponibilidade visíveis para o usuário.

**Permissões:** ver a seção "Permissões" abaixo — a regra é a capability
`view_all_availability`, não o nome do grupo.

## Permissões

> 🔴 **Reescrito em 2026-07-24.** As duas tabelas anteriores estavam erradas em dois pontos:
> diziam que **Controle é BLOQUEADO** na grade mensal (é o oposto — Controle é privilegiado) e
> que **Superintendência vê todos os bloqueios** (não vê).
>
> O eixo real é a capability **`view_all_availability`**. Desde o PR 12 (modo padrão `lotacao`) ela
> vem do **pacote do perfil** da gerência, pelo vínculo `EQUIPE`/`GERENTE` vigente: perfis
> `CONTROLE` e `ADMIN_OPERACIONAL` (DAT), em `apps/core/services/rbac_pacotes.py`. O seed
> (`group_names=("Controle", "DAT")` em `apps/core/services/functional_permissions_seed.py`) só dá
> poder no modo de emergência `uniao`. A matriz muda só por PR e o Django Admin é somente leitura
> (D21); `rbac_diff --auditar` confere banco = seed no pós-deploy.

### Grade Mensal (`MonthlyAvailabilityView`)

`permission_classes` de `MonthlyAvailabilityView` inclui `CanViewAllAvailability` (`apps/core/views_availability_monthly.py`).

| Perfil | Acesso |
|--------|--------|
| Superuser | Escopo amplo (`cache_scope="wide"`) |
| **Controle e DAT** (têm `view_all_availability` pelo vínculo na gerência) | Escopo amplo — **não é bloqueado** (`has_wide_scope` no ramo `gerencia_id is None` de `MonthlyAvailabilityView.get`) |
| Com `gerencia_id` | Apenas se o usuário atua na gerência (papel G/C/A vigente; senão 403) |
| Sem `gerencia_id`, com vínculo | Usuários das próprias gerências via `EquipeGerencia.gerencias_de_atuacao` (mesmo ramo, sem `has_wide_scope`) |
| Sem `gerencia_id`, sem vínculo | **403** — `HasSectorAccess` nega quem não tem papel G/C/A vigente em gerência ativa (`EquipeGerencia.gerencias_de_atuacao`) nem `view_all_availability`; Formador sozinho também dá 403. O ramo "só o próprio usuário" da view não é alcançado |

> ⚠️ O docstring de `MonthlyAvailabilityView` (`views_availability_monthly.py`) ainda repete o texto antigo
> "Controle: BLOQUEADO". O comentário autoritativo é o que abre o ramo `gerencia_id is None` em
> `MonthlyAvailabilityView.get` ("Sem gerencia_id, restringir escopo..."). Drift no código.

### Bloqueios (`AvailabilityBlockViewSet`)

`permission_classes = [IsAuthenticated]` (em `AvailabilityBlockViewSet`, `apps/core/views_availability.py`); o escopo é
aplicado em `get_queryset`, invariante travado por `test_availability_privileged_invariant.py`
(ver o comentário `Invariante` em `is_privileged_user`, `views_availability.py`). "Privilegiado" =
`user_has_policy(user, "view_all_availability")` (em `is_privileged_user`, `views_availability.py`).

| Perfil | Visualização |
|--------|--------------|
| Superuser | Todos os bloqueios |
| **Controle e DAT** | Todos os bloqueios |
| **Superintendência** | ❌ **Não** — não tem `view_all_availability`; cai na regra de gerência |
| G/C/A vigente em gerência ativa | Bloqueios das pessoas da gerência (`AvailabilityBlockViewSet.get_queryset`, `views_availability.py`) |
| Demais (inclusive Formador) | Só os próprios (decisão do dono P9-1, 15/10/2026) |

### Delegação de bloqueio: criar, editar e apagar em nome de outro (PR 13)

`user_can_delegate_availability_block` (`apps/core/rbac/policies.py`) permite que
superuser, o Controle (`operate_preagenda`) e o DAT (`manage_admin_registries`) criem bloqueio **em nome de** um Formador
e editem ou apaguem bloqueio alheio (`AvailabilityBlockViewSet._assert_can_mutate`).
Cada operação registra `AuditLog`: `DELEGATE_BLOCK_CREATE`, `DELEGATE_BLOCK_UPDATE` ou `DELEGATE_BLOCK_DELETE`.

⚠️ O **import** de bloqueios (rota só do superusuário, `SuperuserOnly` em
`views_import_bloqueios.py`) não passa por essa policy: grava `created_by` = quem rodou e um
`AuditLog` `DELEGATE_BLOCK_CREATE`, mas o bloco segue **auto-aprovado**. A partir de 31/07/2026 o
alvo precisa ser Formador ativo (`bloqueios_import.py`) — ver
[imports/disponibilidade.md](./imports/disponibilidade.md) e issue
[#1643](https://github.com/matheusnorjosa/aprender_sistema/issues/1643).

## Gerências e Setores

| Gerência | Setor | Fluxo |
|----------|-------|-------|
| SUPERINTENDENCIA | Super | SUPER |
| GERENCIA 2 | Vidas | NAO_SUPER |
| GERENCIA 3 | Fluir | NAO_SUPER |
| GERENCIA 4 | ACerta | NAO_SUPER |
| GERENCIA 5 | Brincando | NAO_SUPER |
| GERENCIA 6 | Sou da Paz | NAO_SUPER |
| GERENCIA INDIVIDUAL | Individual | NAO_SUPER |

## Vínculo de Usuários

Usuários são vinculados a gerências através da tabela `EquipeGerencia`:

```
Usuario ─── EquipeGerencia ─── Gerencia
              │
              └─ papel (GERENTE, COORDENADOR, APOIO, FORMADOR, EQUIPE)
```

Valores reais de `PAPEL_CHOICES` em `apps/core/models/organizacao.py`. `EQUIPE` (Equipe
administrativa) só diz "trabalha neste setor": não conta como vínculo de escopo na grade, mas dá o
pacote do perfil da gerência (no Controle e no DAT o pacote traz `view_all_availability`, o que dá
escopo amplo). Na grade, só G/C/A vigente conta como vínculo; Formador sozinho recebe 403.
*(Corrigido em 2026-07-24: não existe `APOIO_COORDENACAO`; o valor é `APOIO`.)*

O vínculo em `EquipeGerencia` é o que define o escopo **para quem não é privilegiado**.
Superusers (bypass de superuser em `user_has_policy`, `rbac/policies.py`) e portadores de `view_all_availability` **não** dependem
dele — ver "Permissões" acima.

## Cache

A grade mensal é cacheada no Redis por 5 minutos + jitter de até 30 s
(`_ttl_with_jitter` em `apps/core/utils/cache_utils.py`, usado em `MonthlyAvailabilityView.get`, `views_availability_monthly.py`).

Chave real (`chave_cache_grade` em `views_availability_monthly.py`, a SSOT):

```
monthly:v8:{monthly_ver}:{sha256 do JSON [year, month, role, cache_scope, setor, busca, teto]}
```

- `v8` (F8, scan de 16/10/2026): os parâmetros entram num JSON e a chave usa o hash dele. O setor
  ausente é `null` (não mais `'*'`), então `sector=*` não colide com a grade sem filtro, e um `:` no
  setor ou na busca não desloca os campos. Setor sem espaço nas pontas (vazio = sem filtro), busca
  sem caixa.

- `teto` = o teto de horas por evento vigente (`parametros_disponibilidade()`); salvar um teto
  novo em Configurações vale na consulta seguinte. `v6` entrou em 05/10/2026 com a CH com teto;
  `v7`, em 16/10/2026, com o S5 (nome e e-mail sem CPF, `q` com dígito não casa o e-mail).

- `monthly_ver` = `get_monthly_cache_version()` (em `MonthlyAvailabilityView.get`), a versão única
  `monthly_ver:__global__`. Toda mudança de bloqueio, evento ou participação sobe essa versão
  (`invalidate_availability_cache` → `_invalidate_monthly_cache`), então a grade de **todos** que olham
  refaz na consulta seguinte, sem varrer o Redis. Até 26/10/2026 (item 38) a chave levava a versão de
  quem olha e a mudança subia só a do dono: a agenda de outra pessoa ficava velha por até ~5 min.
- `cache_scope` ∈ `{"wide", "user:{id}", "gerencia:{id}"}` (decidido no ramo de `gerencia_id` de `MonthlyAvailabilityView.get`) — **substitui** o
  `gerencia_id` cru da chave antiga. É o que impede vazamento entre escopos.

*(Corrigido em 2026-07-24: a chave documentada era `monthly:v3:...:{gerencia_id}:...`, de duas
versões atrás.)*

## Endpoints relacionados não cobertos aqui

- `POST /api/availability/check/` e `/check-many/` (rotas `availability-check` / `availability-check-many` em `apps/core/urls.py`) — autorização
  por `can_check_availability_for_others` (`views_availability.py`), distinta da regra
  de leitura acima. A resposta separa `conflicts` (barra: sobreposição, bloqueio, deslocamento)
  de `warnings` (só avisa; hoje sempre vazio). O limite diário (M) não impede nada desde
  02/10/2026 e não é mais emitido desde 05/10/2026, por decisão do dono
  ([regras-disponibilidade.spec](./specs/domain/regras-disponibilidade.spec.md)).

## Referências

- [PLAN_multi_sector_availability.md](./_archive/plans/PLAN_multi_sector_availability.md) - Plano de implementação
- **RD-01..RD-08**: as regras de disponibilidade **não estão neste guia**. O SSOT é o docstring de
  módulo `apps/core/services/availability_service.py` (definição) e
  `apps/core/services/solicitacao_availability.py` (enforcement), além do
  [ADR-003](../../docs/architecture/project-decisions/ADR-003-availability-rules-timezone.md).
- Epic #379 - Disponibilidade Multi-Setor
