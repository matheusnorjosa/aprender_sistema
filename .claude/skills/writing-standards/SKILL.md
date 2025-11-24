---
name: writing-standards
description: Technical writing standards for documentation, docstrings, commit messages, and communication. Use when writing README files, docstrings (PEP 257), PR descriptions, error messages, or technical docs. Focuses on clarity, brevity, active voice, and Python/Django conventions.
---

# Writing Standards — AS v2

Standards for all written technical content: documentation, docstrings, commit messages, error messages, technical communication.

## When to Use This Skill

- Writing **docstrings** (PEP 257 compliance)
- Crafting **commit messages** (conventional commits)
- Creating **PR descriptions**
- Documenting **architecture decisions**
- Writing **user-facing error messages**
- Creating **README files** and technical docs
- Code reviews and feedback

## Core Principles

### 1. Be Concise
- **Every word must earn its place**
- Delete redundant words
- Cut the clutter
- Short sentences convey ideas clearly

**Examples**:
- ❌ "In order to check conflicts" → ✅ "To check conflicts"
- ❌ "This function is able to validate" → ✅ "This function validates"

### 2. Active Voice
Prefer active voice over passive:

- ✅ "We fixed the bug" / "The service checks conflicts"
- ❌ "The bug was fixed by us" / "Conflicts are checked by the service"

### 3. One Idea Per Sentence
- Write short sentences (max 25 words)
- Each sentence expresses one clear idea
- Complex ideas get multiple sentences

**Example**:
```
❌ Bad (3 ideas in 1 sentence):
"The approval service validates permissions, logs the action
to AuditLog, and updates the solicitação status to 'aprovado'."

✅ Good (3 sentences):
"The approval service validates permissions first.
It logs the action to AuditLog.
Finally, it updates the solicitação status to 'aprovado'."
```

### 4. Lead with Results
- Put the outcome first
- Make conclusions obvious
- Don't bury the lead

**Examples**:
- ✅ "The refactor improved performance by 40%. We optimized database queries and added caching."
- ❌ "We optimized database queries and added caching, which improved performance by 40%."

## Naming in Writing

### Descriptive Names (Python/Django)
- Code is reference, history, and functionality
- Names must be readable as a journal
- Be specific and concrete

**Python conventions**:
- Functions/methods: `snake_case` (e.g., `check_availability_conflicts`)
- Classes: `UpperCamelCase` (e.g., `Solicitacao`, `Usuario`)
- Constants: `SNAKE_CAPS` (e.g., `ETL_MAX_DUPLICATES_PCT`)

### Avoid Vague Terms
Replace generic terms with specific ones:

- ❌ `data`, `info`, `stuff`, `manager`, `helper`, `handler`
- ✅ `solicitacao_pendente`, `usuario_aprovador`, `municipio_origem`

### Remove Redundancy
- ✅ `users` (not `user_list` or `users_array`)
- ✅ `approve_solicitacao()` (not `approve_solicitacao_function()`)

## Documentation Standards

### README Files
**Structure** (keep under 200 lines):
1. **What it does** (one sentence)
2. **Why it exists** (one paragraph)
3. **How to use it** (clear steps)
4. **Examples** (if needed)
5. **Link to additional docs** (if extensive)

**Example**:
```markdown
# Availability Service

Checks conflicts for solicitações following RD-01 to RD-08.

This service centralizes conflict detection logic (overlaps,
blocks, travel buffers, daily capacity) to ensure data
consistency and compliance with business rules.

## Usage
\`\`\`python
from apps.core.services import availability_service

result = availability_service.check_conflicts(
    usuario=formador,
    inicio=datetime(...),
    fim=datetime(...),
    municipio=municipio_fortaleza
)
\`\`\`

See [ARCHITECTURE.md](./docs/ARCHITECTURE.md) for details.
```

### Docstrings (PEP 257)

**Python requires docstrings** for public functions/classes. This is NOT optional.

**Format** (Google-style):
```python
def check_conflicts(
    usuario: Usuario,
    inicio: datetime,
    fim: datetime,
    municipio: Municipio
) -> AvailabilityResult:
    """
    Check availability conflicts following RD-01 to RD-08.

    Args:
        usuario: Usuario instance (formador)
        inicio: Start datetime (aware, America/Fortaleza)
        fim: End datetime (aware, America/Fortaleza)
        municipio: Municipio instance for the event

    Returns:
        AvailabilityResult with list of ConflictDetail instances.
        Empty list if no conflicts found.

    Raises:
        ValueError: If fim <= inicio or timezone-naive datetimes
    """
```

**When to use docstrings**:
- ✅ All public functions/methods
- ✅ All classes
- ✅ Complex algorithms
- ✅ Service layer functions
- ❌ Private methods (optional, only if complex)
- ❌ Obvious getters/setters

### Inline Comments (When to Use)

**98% of comments should be functions/variables**, but inline comments are useful for:

1. **WHY, not WHAT**:
   ```python
   # PA-05: Persistent audit required for compliance
   AuditLog.objects.create(usuario=user, action='APPROVE', ...)
   ```

2. **Business context**:
   ```python
   # Superintendência may override conflicts with human context
   # (political priorities, informal negotiations, etc.)
   if user.is_superintendencia:
       approve_without_recheck()
   ```

3. **Gotchas/surprises**:
   ```python
   # IMPORTANT: Don't use select_related here! Causes N+1 due to
   # prefetch_related on participacoes in the next line
   solicitacoes = Solicitacao.objects.all()
   ```

### Commit Messages

**Format** (conventional commits):
```
<type>(<scope>): <message>

feat(core): add conflict detection service (RD-01 to RD-08)
fix(etl): handle empty CSV files gracefully
docs(readme): update Docker setup instructions
```

**Rules**:
- Use imperative mood ("Add" not "Added" or "Adds")
- Be specific about what changed
- Include context if not obvious
- Max 72 characters for first line
- **Never include "Claude Code"** in messages

**Examples**:
- ✅ `feat(approval): add PA-05 audit log persistence`
- ✅ `fix(gcal): retry with exponential backoff on 429`
- ❌ `Fixed stuff`
- ❌ `Updates`
- ❌ `Claude Code: Added feature`

### PR Descriptions

**Structure**:
```markdown
## What
[One sentence describing the change]

## Why
[One paragraph explaining motivation and context]

## Changes
- [Bullet point summary of key changes]
- [Focus on WHAT changed, not HOW]

## Testing
[How this was tested - commands run, tests added]

## Compliance
[If applicable: CP/RD/PA rules validated]
```

**Example**:
```markdown
## What
Implements PA-05: Persistent AuditLog for approval actions.

## Why
PA-05 requires persistent audit trail (not just logger.info)
for compliance. Previous implementation only logged to stdout.

## Changes
- Added AuditLog.objects.create() in approve() and reject()
- Captures: usuario, action, details, ip_address, user_agent
- Added test_approval_flow_records_audit_log() (passing)

## Testing
\`\`\`bash
pytest apps/core/tests/test_approval_policy_PA.py::test_approval_flow_records_audit_log -v
# PASSED
\`\`\`

## Compliance
✅ PA-05: Persistent audit with all required fields
```

## Technical Writing

### Headers
- Short, descriptive, sentence-case
- Make content scannable
- Use hierarchy properly (H1 → H2 → H3)
- Don't skip levels (H1 → H3 ❌)

### Lists
- Use for related items only
- Keep items parallel in structure
- Prefer prose when 2 items or less

**Example**:
```markdown
❌ Bad (not parallel):
- Type hints mandatory
- You should use early returns
- Descriptive naming

✅ Good (parallel):
- Use type hints on all functions
- Use early returns (avoid nesting)
- Use descriptive names (no vague terms)
```

### Examples
- **Show, don't just tell**
- Use real code, not pseudocode
- Keep examples minimal and focused
- Include expected output when helpful

## Writing Anti-Patterns

### Avoid
- **Redundant words**: "in order to" → "to"
- **Weak verbs**: "is able to" → "can"
- **Passive voice**: "was fixed by" → "fixed"
- **Hedging**: "might", "possibly", "perhaps" (when you know the answer)
- **Jargon without explanation**: Define terms on first use
- **Over-explaining obvious things**: Trust the reader's intelligence

### Watch For
- Long sentences (>25 words)
- Dense paragraphs (>5 sentences)
- Nested clauses
- Ambiguous pronouns ("it", "this", "that" without clear referent)

## Specific Use Cases

### Error Messages (User-Facing)

**Format**: `<What happened>. <What to do>.`

**Examples**:
- ✅ `Solicitação not found. Check the ID and try again.`
- ✅ `Approval failed: User lacks Superintendência permission.`
- ✅ `Conflict detected (RD-02): Total block from 09:00 to 12:00.`
- ❌ `An error occurred.`
- ❌ `Something went wrong.`
- ❌ `Error: 500` (no context)

**Tone**: Helpful, not condescending. Assume intelligence, not knowledge.

### API Documentation (DRF Serializers)

**Include**:
1. Purpose (one sentence)
2. Fields (with types and constraints)
3. Example request/response
4. Error cases (if complex)

**Example**:
```python
class SolicitacaoSerializer(serializers.ModelSerializer[Solicitacao]):
    """
    Serializer for Solicitacao model.

    Read-only fields: id, created_at, meet_link
    Required fields: projeto, municipio, inicio, fim
    Optional fields: descricao, is_online

    Example POST request:
    {
        "projeto": 1,
        "municipio": 5,
        "inicio": "2025-01-15T09:00:00-03:00",
        "fim": "2025-01-15T12:00:00-03:00",
        "descricao": "Formação ACerta",
        "is_online": false
    }

    Validation errors:
    - 400: fim <= inicio
    - 400: timezone-naive datetimes
    - 403: User lacks permissions
    """
```

## Tone Guidelines

### Technical Writing
- Professional but approachable
- Clear and direct
- Avoid humor in error messages
- Be helpful, not condescending

### Documentation
- Assume intelligence, not knowledge
- Explain context, not obvious things
- Guide, don't command

**Examples**:
- ✅ "This service validates conflicts. See RD-01 to RD-08 for rules."
- ❌ "You need to make sure you validate conflicts properly or things will break."

### Code Reviews
- Focus on code, not the person
- Suggest alternatives, don't just criticize
- Explain WHY, not just WHAT to change

**Examples**:
- ✅ "Consider extracting this to a service function for testability."
- ❌ "This is wrong. Put it in a service."

## Review Checklist

Before publishing writing:
- [ ] Lead with the result/conclusion
- [ ] Every sentence has one clear idea
- [ ] Active voice used throughout
- [ ] No redundant words
- [ ] Specific terms (no vague language)
- [ ] Short sentences (<25 words)
- [ ] Clear hierarchy (if using headers)
- [ ] Examples included (if needed)
- [ ] Scannable and skimmable
- [ ] Docstrings follow PEP 257
- [ ] Commit messages follow conventional commits

---

## References

- **PEP 257**: Docstring Conventions (https://peps.python.org/pep-0257/)
- **Conventional Commits**: https://www.conventionalcommits.org/
- **CLAUDE-principles.md**: Code quality standards
- **ISO 9241-110**: Ergonomics principles (applies to documentation too)

---

**Adapted from**: Premium Claude Code Package (TypeScript/React)
**Customized for**: AS v2 (Python/Django)
**Last Updated**: 2025-11-24
