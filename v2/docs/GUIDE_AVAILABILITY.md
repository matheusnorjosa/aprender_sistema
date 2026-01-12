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
| `gerencia_id` | int | Não | ID da gerência. Se omitido, assume SUPERINTENDENCIA (SUPER) |
| `sector` | string | Não | Filtro por nome do projeto |
| `q` | string | Não | Filtro por nome/email do formador |

**Exemplos:**

```bash
# Grade da Superintendência (comportamento padrão)
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

**Permissões:**

- **Privilegiados** (superuser, Superintendência, Controle): veem todos os bloqueios
- **Outros usuários**: veem bloqueios de usuários da mesma gerência

## Permissões

### Grade Mensal (MonthlyAvailabilityView)

| Perfil | Acesso |
|--------|--------|
| Superuser | Todas as gerências |
| Controle | **BLOQUEADO** |
| Com `gerencia_id` | Apenas se usuário pertence à gerência |
| Sem `gerencia_id` | Assume SUPER (comportamento atual) |

### Bloqueios (AvailabilityBlockViewSet)

| Perfil | Visualização |
|--------|--------------|
| Superuser | Todos os bloqueios |
| Superintendência | Todos os bloqueios |
| Controle | Todos os bloqueios |
| Outros | Bloqueios da mesma gerência |

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
              └─ papel (FORMADOR, COORDENADOR, APOIO_COORDENACAO, GERENTE)
```

Um usuário só pode acessar dados de uma gerência se tiver um registro em `EquipeGerencia` para essa gerência.

## Cache

A grade mensal é cacheada no Redis por 5 minutos. A chave de cache inclui todos os parâmetros:

```
monthly:v3:{year}:{month}:{role}:{gerencia_id}:{sector}:{q}
```

## Referências

- [PLAN_multi_sector_availability.md](./PLAN_multi_sector_availability.md) - Plano de implementação
- Epic #379 - Disponibilidade Multi-Setor
