# Specs — Spec-Driven Development de mudança

Este diretório é a **fonte versionada** de como conduzimos **cada mudança** no Aprender
Sistema v2. Qualquer agente (Claude, Zed, Cursor, humano) deve ler **`CONSTITUTION.md`
primeiro** e seguir o fluxo abaixo antes de escrever código.

> **Não confundir com [`v2/docs/specs/`](../v2/docs/specs/INDEX_SDD.md).** Aquela camada
> (formalizada na [ADR-017](../docs/architecture/project-decisions/ADR-017-spec-driven-documentation.md))
> é a **documentação viva dos módulos que já existem** — uma spec por módulo/contrato, com
> frontmatter e `sources_of_truth`. **Esta** pasta (`specs/`) é o **processo por mudança**:
> uma spec efêmera (requirements → design → tasks) por feature/fix em andamento. Mesma
> filosofia (spec antes do código), granularidades diferentes.
>
> Por que aqui e não em `.claude/`? A pasta `.claude/` é gitignored (local, só o Claude
> Code vê). `specs/` é versionado: viaja pelo repositório e é visível a **qualquer**
> agente, em qualquer máquina. Os **contratos enforced** (CP, RD, PA, RF) têm SSOT em
> `docs/business-rules/` e nas specs de `v2/docs/specs/domain/` (ADR-017 §6): onde houver
> divergência, **essas fontes mandam** — `CONSTITUTION.md` aqui é um resumo operacional e
> `.claude/` traz a profundidade extra para o Claude Code.

---

## O que é Spec-Driven Development aqui

Toda mudança não-trivial nasce de uma **spec** antes do código. A spec é três arquivos,
nesta ordem — cada um responde uma pergunta:

| Arquivo | Pergunta | Foco |
|---|---|---|
| `requirements.md` | **O quê / por quê** | User stories, critérios de aceite, RF/RD/PA/CP afetados |
| `design.md` | **Como** | Camadas tocadas, modelo de dados, API, ADRs, estratégia de teste |
| `tasks.md` | **Em que ordem** | Checklist executável em ordem TDD, com verificação e gate |

Trivial (typo, bump de dep, ajuste de 1 linha) não precisa de spec — vá direto ao commit
convencional. Na dúvida, escreva a spec: ela é barata e evita retrabalho.

---

## Fluxo (lifecycle)

```text
1. requirements  →  2. design  →  3. tasks  →  4. implementar (TDD)  →  5. verificar  →  6. PR
   (o quê/porquê)     (como)        (ordem)      red → green → refactor   gate verde      humano aprova
```

1. **requirements** — capture o problema e os critérios de aceite **testáveis**. Referencie
   as regras de negócio aplicáveis (RF/RD/PA/CP) por código, não por paráfrase.
2. **design** — decida a abordagem dentro das camadas (`models → services → views`),
   liste arquivos a tocar, contratos de API, e como vai testar. Cite ADRs relevantes.
3. **tasks** — quebre em passos pequenos, **cada um com seu teste antes**. Inclua o passo
   de verificação e o staging gate.
4. **implementar** — siga `tasks.md`. Red → Green → Refactor. Não pule etapas (CP-04).
5. **verificar** — rode os testes e veja o verde; rode lint/tipos; confira regressão.
   Não declare pronto sem isso (ver `CONSTITUTION.md` § Verification gate).
6. **PR** — só com staging gate `ALL 8 CHECKS PASSED` + evidência. **Só o humano** abre/
   mergeia o PR (CP-07): o agente para no verde e relata.

---

## Convenção de pastas

Uma spec por mudança, numerada e com slug:

```text
specs/
├── README.md                       ← este arquivo (o método)
├── CONSTITUTION.md                 ← princípios imutáveis (leia primeiro)
├── templates/                      ← copie para iniciar uma spec nova
│   ├── requirements.md
│   ├── design.md
│   └── tasks.md
└── NNNN-slug-curto/                ← uma feature/fix (ex.: 0001-example-auditlog-edit)
    ├── requirements.md
    ├── design.md
    └── tasks.md
```

Para começar: `cp -r specs/templates specs/NNNN-minha-feature` e preencha na ordem.
`NNNN` = próximo número livre (4 dígitos). O slug deve casar com o nome da branch
(`<tipo>/NNNN-slug`).

---

## Relação com o que já existe

- **`v2/docs/specs/`** (ADR-017) — documentação viva **por módulo** já existente. Uma spec
  daqui *implementa* uma mudança; uma spec de lá *descreve* o módulo depois de pronto. Ao
  fechar uma mudança que altera contrato de módulo, atualize a spec viva correspondente.
- **Contratos de negócio (SSOT):** `docs/business-rules/` (CP/PA/RD/RF) — não reescreva os
  códigos aqui, **referencie** por código.
- **Não duplica** os planos de produto em `v2/docs/plans/` nem as notas em `thoughts/`.
  Specs aqui são o contrato executável de **uma** mudança; planos lá são estratégia ampla.
- Regras profundas: `.claude/CLAUDE.md`, `.claude/rules/`, `.claude/skills/aprender-domain/`.
- Ambientes/comandos: `v2/infra/ENVIRONMENTS.md`.

---

## Exemplo real

`specs/0001-example-auditlog-edit/` — spec preenchida da reabilitação do teste de
AuditLog de edição de Solicitação. Use como referência de granularidade e tom.
