# Regras de Disponibilidade (RD)

Regras que governam a verificação de conflitos de agenda.

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

- Entre **municípios distintos**: tempo mínimo de deslocamento (60-120 min)
- **Mesmo município**: buffer pode ser zero

## RD-05: Capacidade Diária (M)

Formador não pode ter mais de **N horas** de eventos por dia (configurável).

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
- Tipo de conflito (E, M, D, P, T, X)

## Códigos de Conflito

| Código | Significado |
|--------|-------------|
| E | Evento existente (overlap) |
| M | Mais de um evento (capacidade) |
| D | Deslocamento insuficiente |
| P | Bloqueio parcial |
| T | Bloqueio total |
| X | Outro conflito |
