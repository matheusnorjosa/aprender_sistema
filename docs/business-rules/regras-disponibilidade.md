# Regras de Disponibilidade (RD)

Regras que governam a verificação de conflitos de agenda.

!!! info "SSOT técnica"
    O contrato detalhado — camada consultiva vs. de enforcement, quem é checado, locking, e o
    registro das divergências entre a regra e o código (hoje resolvidas) — está em
    [`v2/docs/specs/domain/regras-disponibilidade.spec.md`](https://github.com/matheusnorjosa/aprender_sistema/blob/main/v2/docs/specs/domain/regras-disponibilidade.spec.md).
    Esta página é o resumo legível. Em caso de conflito, a spec vence.

!!! note "Consultivo **e** bloqueante"
    Desde o #1452 a checagem tem duas camadas: `check_conflicts` (consultiva, cache de 5 min,
    usada pelas telas) e `check_conflicts_uncached` via `enforce_solicitacao_availability`
    (enforcement, sem cache, dentro da transação). A segunda **bloqueia** criação, edição e
    aprovação com HTTP 400 `availability_conflict`, para todos os participantes do evento —
    não só quem criou. Conflito é bloqueio duro, sem override, inclusive no fluxo `NAO_SUPER`.

## RD-01: Não-Sobreposição

- Formador não pode ter dois eventos que se sobreponham
- Caso borda: `fim == início` → **não conflita**
- Overlap ≥ 1 minuto → **conflito**

## RD-02: Bloqueio Total (T)

Bloqueio marcado como **T** impede quaisquer eventos no intervalo.

## RD-03: Bloqueio Parcial (P)

Bloqueio **P** impede eventos dentro do subintervalo bloqueado.
Fora do subintervalo → permitido.

## RD-04: Buffer de Deslocamento (D)

- Entre **municípios distintos**: tempo mínimo de deslocamento — `TRAVEL_BUFFER_MINUTES`,
  default **120 min** (`TRAVEL_BUFFER_MINUTES` em `config/settings.py`), sobrescrevível em runtime
- **Mesmo município**: buffer pode ser zero
- Gap **exatamente igual** ao buffer passa; só `< buffer` conflita
- Município ausente em qualquer lado é tratado como **cidade diferente** → exige buffer

## RD-05: Teto de Horas de Formação (não é conflito de agenda)

Desde a decisão do dono de 05/10/2026 o RD-05 **não barra nem avisa** na agenda: o evento pode
ter quantas horas quiser e o motor não emite mais o código `M`. O parâmetro
`AVAILABILITY_DAILY_LIMIT_HOURS` (default **8 h**, em `config/settings.py`, ajustável em
Configurações) virou o **teto por evento** da contagem de horas de formação:
`min(fim − início, teto)`, somado no dia local do início, sem teto por dia. SSOT:
`apps/core/services/horas_formacao.py`, usada pela Grade Mensal e pelo painel de Equipe.

## RD-06: Timezone

- Comparações **timezone-aware** usando `America/Fortaleza`
- Armazenar em UTC, comparar no TZ do projeto

## RD-07: Prioridade de Checagem

1. Bloqueios (T, P)
2. Conflitos por eventos aprovados
3. Buffer de deslocamento (D)

## RD-08: Mensagens de Conflito

Mensagens devem incluir:

- Formador(es) em conflito
- Data e intervalo (HH:MM dd/mm)
- Tipo de conflito (D, P, T, X)

## Códigos de Conflito

| Código | Significado |
|--------|-------------|
| X | Sobreposição de eventos (overlap) |
| D | Deslocamento insuficiente |
| P | Bloqueio parcial |
| T | Bloqueio total |

!!! note "`E` não é código de conflito"
    `E` existe no tipo `ConflictCode` mas **nunca** é emitido pela checagem. `E`, `D1` e `2` são
    códigos de **célula da Grade Mensal** (legenda de `GUIDE_AVAILABILITY.md`), não saídas de
    `check_conflicts`. Não misturar as duas legendas.

## Quem é checado

Desde a decisão do dono de 05/10/2026, só ocupa a agenda quem tem papel `FORMADOR` no evento
(`ENFORCED_ROLES` em `apps/core/services/availability_service.py`) e, quando o evento tem
`coordenador_acompanha=True`, o coordenador responsável (`coordenador_ocupante`). Quem criou
não entra por ter criado; `COORDENADOR`, `COORD_ACOMPANHA` e `CONVIDADO` não ocupam (servem ao
convite do Google).

As duas pontas usam a mesma regra: o enforcement (`collect_participants`) decide **quem** é
checado, e a query dos eventos **já existentes** filtra pelo mesmo predicado
`ocupa_agenda_q` (#1664). Quem foi só convidado a um evento continua livre para ser alocado
em outro.
