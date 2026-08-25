---
name: subagent-development
description: Orquestra subagents no AS v2 — decompõe a tarefa em domínios independentes, paraleliza e revisa em 2 estágios. Use ao delegar exploração, implementação ou validação cross-arquivo para acelerar o trabalho e poupar o contexto principal.
---

# Subagent Development

Orquestrar subagents especializados (delegar, paralelizar, revisar) para acelerar
trabalho cross-arquivo e poupar o contexto principal.

> **SSOT**: a política de delegação do projeto vive na seção **"Delegação a subagents"**
> do `.claude/CLAUDE.md`. Esta skill é o *como operacional*; não duplique a política — linke.

## Agent types disponíveis

Use exatamente estes `subagent_type` (não invente outros):

- **Explore** — busca/varredura/investigação cross-arquivo (read-only).
- **Plan** — arquitetar antes de implementar.
- **general-purpose** — multi-step (implementar, rodar testes, validar).
- **Workflow** — fan-out por cluster/finding em auditorias, migrações e revisões grandes.

## When to Use

- Feature complexa com múltiplos workstreams independentes.
- Tarefa que se beneficia de foco especializado.
- Trabalho que envolve **ler muitos arquivos** → delegue e fique só com a conclusão.

### NÃO paralelize quando

- Falhas estão relacionadas (mesma root cause).
- Requer entendimento do sistema completo / estado compartilhado.
- Mudanças podem conflitar entre si.

## Process

### 1. Decompor por domínio independente

Quebre a feature em unidades que **não compartilham contexto**:

- **Exploração** — análise de codebase, descoberta de padrões.
- **Implementação** — escrever código, testes.
- **Validação** — type check, lint, rodar testes.

Agrupe pelo que está quebrado/isolado:

```
Exemplo: 6 testes falhando
├── test_availability.py (3 falhas) → Domínio: Disponibilidade (RD-01~08)
├── test_approval.py    (2 falhas) → Domínio: Aprovação (PA-01~07)
└── test_gcal.py        (1 falha)  → Domínio: Google Calendar
```

### 2. Spawn subagents

Use a Task tool com o agent type adequado. Lance agents independentes
**em paralelo** (uma mensagem, vários tool calls):

```
Task(subagent_type="Explore", prompt="Find all places where X pattern is used")
Task(subagent_type="Plan", prompt="Design the architecture for feature Y")
Task(subagent_type="general-purpose", prompt="Run the test suite for module Z and report failures")
```

Cada agent precisa de:

- **Escopo específico** — apenas seu domínio (arquivos nomeados).
- **Goal claro** — o que significa "done".
- **Constraints** — o que NÃO fazer.
- **Output esperado** — formato do deliverable.

#### Prompt BOM (paralelizar correção de testes)

```
Fix os testes em test_availability.py.

Contexto:
- 3 testes falhando: test_check_overlap, test_block_total, test_buffer
- Erro comum: "AssertionError: timezone mismatch"
- Causa provável: datetime.now() vs America/Fortaleza

Constraints:
- NÃO altere código de produção (apps/core/services/)
- NÃO altere outros arquivos de teste
- USE freezegun para fixar tempo

Deliverable:
- Testes passando (docker exec aprender_dev-web-1 pytest ...)
```

#### Prompt RUIM

```
Fix all tests.
```

Sem escopo, sem contexto, sem constraints, sem deliverable — o agent adivinha.

### 3. Two-Stage Review

**Stage 1 — Subagent Completion**
Quando o subagent retorna:
- Leia o output completo.
- Verifique que as claims batem com a evidência.
- Anote gaps ou ressalvas.

**Stage 2 — Integration Review**
Antes de apresentar ao usuário:
- Cross-check dos outputs por consistência.
- Verifique que os fixes paralelos não conflitam.
- Rode validação de integração (testes todos juntos, type check).

### 4. Synthesize Results

Combine os outputs em uma resposta coerente:
- Resuma os achados-chave (não despeje o dump do subagent).
- Apresente plano/implementação unificada.
- Sinalize conflitos não resolvidos.

## Pitfalls Comuns

Prompt fraco (escopo/contexto/constraints/deliverable) → ver checklist em
[2. Spawn subagents](#2-spawn-subagents). Os demais riscos:

| Pitfall | Solução |
|---------|---------|
| Blind trust | Sempre verificar as claims do subagent |
| Over-spawning | Não criar agent para tarefa trivial |
| Missing synthesis | Não despejar output bruto no usuário |
| Sequential quando podia ser parallel | Lançar tasks independentes juntas |

## Example

```
User: "Add authentication to the API"

1. Spawn em paralelo (uma mensagem):
   - Explore: "Find current auth patterns in codebase"
   - Explore: "List all unprotected endpoints"
   - Plan: "Design session-based auth flow"

2. Stage 1: revisar cada output; Stage 2: sintetizar plano

3. Spawn implementação:
   - general-purpose: "Implement auth middleware"
   - general-purpose: "Add auth tests"

4. Integration review + rodar suite completa
```

## Integração com Outras Skills

- `verification-gate` antes de declarar sucesso.
- `debugging-and-error-recovery` se um subagent reporta problema.
- `test-driven-development` para o ciclo de implementação delegada.
