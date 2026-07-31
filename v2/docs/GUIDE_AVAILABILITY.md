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
| `q` | string | Não | Filtro por nome/email do formador |

> 🔴 **Corrigido em 2026-07-24.** Este guia dizia que omitir `gerencia_id` "assume
> SUPERINTENDENCIA (SUPER)". **Falso.** Em `apps/core/views_availability_monthly.py:187-213`,
> quando `gerencia_id is None`:
>
> - quem tem a capability `view_all_availability` recebe escopo **amplo** (`:188-190`,
>   `cache_scope="wide"`);
> - os demais são escopados aos usuários das **próprias** gerências via `EquipeGerencia`
>   (`:192-208`);
> - quem não tem vínculo algum vê **apenas a si mesmo** (`:210-212`).
>
> `build_monthly_grid` é então chamado com `gerencia_id=None` **+ `allowed_user_ids`** (`:233-241`).

**Exemplos:**

```bash
# Escopo derivado do usuário (amplo, das próprias gerências, ou só o próprio)
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
> O eixo real é a capability **`view_all_availability`**, atribuída no seed apenas a
> **Controle** e **DAT** (`apps/core/services/functional_permissions_seed.py:171-184`,
> `group_names=("Controle", "DAT")` em `:183`). Como a atribuição é admin-driven (D17), o
> conjunto efetivo em produção **depende de verificação humana** no Django Admin.

### Grade Mensal (`MonthlyAvailabilityView`)

`permission_classes` inclui `CanViewAllAvailability` (`apps/core/views_availability_monthly.py:80`).

| Perfil | Acesso |
|--------|--------|
| Superuser | Escopo amplo (`cache_scope="wide"`) |
| **Controle e DAT** (têm `view_all_availability`) | Escopo amplo — **não é bloqueado** (`:188-190`) |
| Com `gerencia_id` | Apenas se o usuário pertence à gerência |
| Sem `gerencia_id`, com vínculo | Usuários das próprias gerências via `EquipeGerencia` (`:192-208`) |
| Sem `gerencia_id`, sem vínculo | Apenas o próprio usuário (`:210-212`) |

> ⚠️ O docstring em `views_availability_monthly.py:61` ainda repete o texto antigo
> "Controle: BLOQUEADO". O comentário autoritativo é `:13-19` / `:75-79`. Drift no código.

### Bloqueios (`AvailabilityBlockViewSet`)

`permission_classes = [IsAuthenticated]` (`apps/core/views_availability.py:112`); o escopo é
aplicado em `get_queryset`, invariante travado por `test_availability_privileged_invariant.py`
(ver comentário `views_availability.py:46-50`). "Privilegiado" =
`user_has_policy(user, "view_all_availability")` (`views_availability.py:56-58`).

| Perfil | Visualização |
|--------|--------------|
| Superuser | Todos os bloqueios |
| **Controle e DAT** | Todos os bloqueios |
| **Superintendência** | ❌ **Não** — não tem `view_all_availability`; cai na regra de gerência |
| Outros | Bloqueios de usuários da mesma gerência (`views_availability.py:126-136`) |

### Delegação de criação de bloqueio (PR 13)

`user_can_delegate_availability_block` (`apps/core/rbac/policies.py:424-446`) permite que
superuser, Assistente Administrativo do Controle e DAT criem bloqueio **em nome de** um Formador.
A operação registra `AuditLog` `DELEGATE_BLOCK_CREATE`.

⚠️ O **import** de bloqueios não passa por essa policy e cria blocos auto-aprovados **sem
`created_by`** — ver [imports/disponibilidade.md](./imports/disponibilidade.md) e issue
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
              └─ papel (GERENTE, COORDENADOR, APOIO, FORMADOR)
```

Valores reais de `PAPEL_CHOICES` em `apps/core/models/organizacao.py:245-250`.
*(Corrigido em 2026-07-24: não existe `APOIO_COORDENACAO`; o valor é `APOIO`.)*

O vínculo em `EquipeGerencia` é o que define o escopo **para quem não é privilegiado**.
Superusers (`rbac/policies.py:492-493`) e portadores de `view_all_availability` **não** dependem
dele — ver "Permissões" acima.

## Cache

A grade mensal é cacheada no Redis por 5 minutos + jitter de até 30 s
(`apps/core/utils/cache_utils.py:21-27`, usado em `views_availability_monthly.py:252`).

Chave real (`views_availability_monthly.py:221-224`):

```
monthly:v5:{monthly_ver}:{year}:{month}:{role}:{cache_scope}:{sector or '*'}:{q_lower}
```

- `monthly_ver` = `get_monthly_cache_version(request.user.id)` (`:218-220`) — permite invalidar
  por usuário sem varrer o Redis.
- `cache_scope` ∈ `{"wide", "user:{id}", "gerencia:{id}"}` (`:186-215`) — **substitui** o
  `gerencia_id` cru da chave antiga. É o que impede vazamento entre escopos.

*(Corrigido em 2026-07-24: a chave documentada era `monthly:v3:...:{gerencia_id}:...`, de duas
versões atrás.)*

## Endpoints relacionados não cobertos aqui

- `POST /api/availability/check/` e `/check-many/` (`apps/core/urls.py:184-191`) — autorização
  por `can_check_availability_for_others` (`views_availability.py:61-83`), distinta da regra
  de leitura acima.

## Referências

- [PLAN_multi_sector_availability.md](./_archive/plans/PLAN_multi_sector_availability.md) - Plano de implementação
- **RD-01..RD-08**: as regras de disponibilidade **não estão neste guia**. O SSOT é o docstring de
  `apps/core/services/availability_service.py:1-15` (definição) e
  `apps/core/services/solicitacao_availability.py` (enforcement), além do
  [ADR-003](../../docs/architecture/project-decisions/ADR-003-availability-rules-timezone.md).
- Epic #379 - Disponibilidade Multi-Setor
