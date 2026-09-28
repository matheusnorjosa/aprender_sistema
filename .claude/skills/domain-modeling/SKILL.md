---
name: domain-modeling
description: Construir e afiar o modelo de domínio do Aprender Sistema — glossário de termos e ADRs — durante uma conversa de design. Use ao discutir terminologia do negócio, editar o glossário, ou registrar/editar um ADR. Para só consultar regras RF/RD/PA/CP, use `aprender-domain`.
---

# Domain Modeling (Aprender Sistema)

Adaptado de `mattpocock/skills` (MIT) para as convenções deste repo (ADR-017, SDD).

Disciplina *ativa*: desafiar termos, inventar cenários de borda e registrar glossário e
decisões no momento em que se firmam. Só *ler* o glossário não é esta skill.

## Onde as coisas moram

| O quê | Onde |
|---|---|
| Glossário | `v2/docs/specs/domain/glossario.spec.md` |
| ADR | `docs/architecture/project-decisions/ADR-NNN-slug.md` |
| Índice de ADRs | `docs/architecture/project-decisions/README.md` |
| Índice de specs | `v2/docs/specs/INDEX_SDD.md` e `v2/docs/specs/domain/README.md` |

Crie arquivos só quando houver algo a escrever. Ao criar o glossário, registre-o nos dois
índices de specs **no mesmo commit** (ADR-017: nada vivo fora do índice).

## Durante a sessão

### Desafie contra o glossário
Termo usado em conflito com o glossário → aponte na hora: "O glossário define 'Evento' como X,
mas você parece querer dizer Y. Qual dos dois?"

### Afie linguagem vaga
Termo ambíguo ou sobrecarregado → proponha o termo canônico: "'Usuário' aqui é o Formador ou o
Coordenador? São coisas diferentes."

### Cenários concretos
Ao discutir relações do domínio, teste com cenários de borda que forcem a fronteira entre
conceitos (ex.: formador em dois municípios no mesmo dia; projeto que muda de fluxo SUPER).

### Confira com o código
Quando a pessoa afirmar como algo funciona, verifique em `v2/backend/apps/` (models, services).
Contradição → mostre: "O código cancela a Solicitação inteira, mas você disse que cancelamento
parcial existe. Qual está certo?"

### Atualize o glossário na hora
Termo resolvido → escreva no glossário imediatamente, não acumule para o fim.

O glossário é **só vocabulário**: nada de implementação, spec ou rascunho. Regra de negócio
numerada (RF/RD/PA/CP) já tem spec própria — linke, não duplique.

## Formato do glossário

```md
---
title: Glossário do Domínio
status: canonical
last_verified: AAAA-MM-DD
owner: domain
sources_of_truth:
  - v2/backend/apps/core/models/
---

# Glossário do Domínio

Vocabulário canônico do negócio. Voltar ao [índice SDD](../INDEX_SDD.md).

## {Agrupamento, quando surgir}

**Solicitação**:
Pedido de agendamento de um evento de formação, sujeito à política de aprovação (PA).
_Model_: `Solicitacao`
_Evitar_: pedido, requisição
```

Regras:
- **Seja opinativo.** Várias palavras para um conceito → escolha uma, liste as outras em `_Evitar_`.
- **Definição curta.** Uma ou duas frases. Diga o que a coisa *é*, não o que faz.
- **Só termos deste negócio.** Conceito genérico de programação não entra.
- `_Model_` só quando existe um model Django correspondente — confira que existe.
- Atualize `last_verified` e `sources_of_truth` ao conferir termos contra o código.

## ADRs, com parcimônia

Ofereça um ADR só quando as três forem verdadeiras:

1. **Difícil de reverter** — mudar de ideia depois custa caro.
2. **Surpreendente sem contexto** — um leitor futuro vai perguntar "por que assim?".
3. **Resultado de trade-off real** — havia alternativas genuínas.

Faltou uma → sem ADR. A decisão fica na conversa (ou numa spec, se for contrato).

### Numeração
`docs/architecture/project-decisions/` e `v2/docs/adr/` **compartilham um espaço de numeração**.
Próximo número = maior das duas pastas + 1. Depois de criar, rode
`python v2/backend/scripts/check_adr_numbers.py` e adicione a linha no índice `README.md`.

### Template (o do repo, em pt-BR)

```md
# ADR-NNN: {Título}

**Status:** Accepted | Deprecated | Superseded by ADR-YYY
**Date:** AAAA-MM-DD
**Decider:** {nome}

## Context
{O problema que levou à decisão}

## Decision
{O que foi escolhido e por quê}

## Consequences
{O que muda, o que fica proibido, o que é recomendado}

## References
{Specs, código, outros ADRs}
```

Um ADR curto é válido: o valor está em registrar *que* decidiu e *por quê*.
