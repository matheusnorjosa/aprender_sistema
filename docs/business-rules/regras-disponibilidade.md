# Regras de Disponibilidade (RD)

Regras que governam a verificação de conflitos de agenda.

!!! info "SSOT técnica"
    O contrato detalhado — camada consultiva vs. de enforcement, quem é checado, locking, e as
    divergências vivas entre a regra e o código — está em
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
  default **120 min** (`config/settings.py:788`), sobrescrevível em runtime
- **Mesmo município**: buffer pode ser zero
- Gap **exatamente igual** ao buffer passa; só `< buffer` conflita
- Município ausente em qualquer lado é tratado como **cidade diferente** → exige buffer

## RD-05: Capacidade Diária (M)

Formador não pode ter mais de **N horas** de eventos por dia —
`AVAILABILITY_DAILY_LIMIT_HOURS`, default **8 h** (`config/settings.py:785`).

!!! danger "Regra não vale para eventos que cruzam a meia-noite (P2 · #1664)"
    O cálculo avalia **apenas** o dia local de `inicio` e soma o novo intervalo **inteiro**,
    sem recortá-lo ao dia — enquanto os eventos já existentes *são* recortados
    (`apps/core/services/availability_service.py:280-306`). Um evento das 22:00 às 06:00 debita
    480 min no dia 1 (onde só 120 min são reais) e **nada** no dia 2, cuja carga já agendada
    nunca é somada. Falso positivo no dia de início, falso negativo no dia seguinte.

## RD-06: Timezone

- Comparações **timezone-aware** usando `America/Fortaleza`
- Armazenar em UTC, comparar no TZ do projeto

## RD-07: Prioridade de Checagem

1. Bloqueios (T, P)
2. Conflitos por eventos aprovados
3. Buffer de deslocamento (D)
4. Limite diário (M)

## RD-08: Mensagens de Conflito

Mensagens devem incluir:

- Formador(es) em conflito
- Data e intervalo (HH:MM dd/mm)
- Tipo de conflito (M, D, P, T, X)

## Códigos de Conflito

| Código | Significado |
|--------|-------------|
| X | Sobreposição de eventos (overlap) |
| M | Capacidade diária excedida |
| D | Deslocamento insuficiente |
| P | Bloqueio parcial |
| T | Bloqueio total |

!!! note "`E` não é código de conflito"
    `E` existe no tipo `ConflictCode` mas **nunca** é emitido pela checagem. `E`, `D1` e `2` são
    códigos de **célula da Grade Mensal** (legenda de `GUIDE_AVAILABILITY.md`), não saídas de
    `check_conflicts`. Não misturar as duas legendas.

## Quem é checado

O enforcement checa os participantes gravados com papel `COORDENADOR`, `FORMADOR` ou
`COORD_ACOMPANHA`, mais o criador da solicitação. `CONVIDADO` fica de fora **de propósito**:
é audiência, não recurso alocado — checá-lo estouraria a capacidade diária de quem é convidado
a vários eventos no mesmo dia.

!!! warning "As duas pontas discordam (P2 · #1664)"
    A exclusão de `CONVIDADO` vale para decidir **quem** é checado, mas não para a query dos
    eventos **já existentes**, que não filtra papel
    (`apps/core/services/availability_service.py:166-168`). Resultado: quem foi convidado a um
    evento fica indisponível para ser alocado em outro — exatamente o caso que a exclusão de
    `CONVIDADO` existia para evitar.
