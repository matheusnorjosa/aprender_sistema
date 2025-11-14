---
description: Review code for AS v2 compliance (CP, RD, PA, RF, code quality)
argument-hint: [file or directory to review]
---

# Code Review — AS v2 Compliance

Review code: $ARGUMENTS

## Approach:

### 1. Quality Checklist (CLAUDE-principles.md)

#### Type-Safety
- [ ] **Type hints** em todas as funções/métodos
- [ ] **DRF serializers** com validação explícita
- [ ] **Django ORM** usado (sem raw SQL)

#### Naming Conventions
- [ ] **Models/Classes**: `UpperCamelCase` (Usuario, Solicitacao)
- [ ] **Functions/Methods**: `snake_case` (check_conflicts, apply_one)
- [ ] **Constants**: `SNAKE_CAPS` (ETL_MAX_DUPLICATES_PCT)
- [ ] **Descriptive names**: Evitar `data`, `info`, `manager`, `helper`

#### Control Flow
- [ ] **Early returns** (código flat, sem if-else aninhados)
- [ ] **Max 2-3 níveis** de indentação
- [ ] **Hash-lists** ao invés de switch-case (quando aplicável)

#### Comments
- [ ] **98% desnecessários** (convertidos para funções/variáveis)
- [ ] **Docstrings** obrigatórios em funções públicas
- [ ] **WHY, não WHAT** (quando lógica é não-óbvia)

#### Code Organization
- [ ] **Single Responsibility** (1 função = 1 propósito)
- [ ] **DRY** (código não repetido)
- [ ] **Services layer** (business logic fora de views)
- [ ] **Keep code close** (usado 1x = inline, 4+x = módulo separado)

### 2. Django/DRF Patterns

#### Models
- [ ] **Constraints no DB** (CHECK, UNIQUE, FK)
- [ ] **Indexes** em campos de filtro/ordenação
- [ ] **related_name** descritivo
- [ ] **Timezone-aware** (America/Fortaleza, store UTC)

#### Serializers
- [ ] **Read vs Write** separation
- [ ] **Validação explícita** em `validate_*()`
- [ ] **StringRelatedField** para GET, **PrimaryKeyRelatedField** para POST/PUT

#### Views/ViewSets
- [ ] **Thin controllers** (lógica em services)
- [ ] **Permission classes** corretas (IsSuperintendencia, etc.)
- [ ] **Throttling** em endpoints sensíveis
- [ ] **select_related/prefetch** para evitar N+1

#### Services
- [ ] **Business logic** isolada
- [ ] **Type hints** obrigatórios
- [ ] **Early returns**
- [ ] **Testável** (sem side effects ocultos)

### 3. Security (OWASP)

- [ ] **CSRF Protection**: Token em forms POST/PUT/DELETE
- [ ] **SQL Injection**: ORM obrigatório (sem raw SQL)
- [ ] **Secrets**: Via `.env`, nunca hardcoded
- [ ] **RBAC**: Permissions verificadas
- [ ] **Input validation**: Serializers + clean methods
- [ ] **XSS**: Templates escapados (Django default)

### 4. Performance

- [ ] **select_related** para FKs (1:1, N:1)
- [ ] **prefetch_related** para M2M
- [ ] **Índices DB** em campos de filtro
- [ ] **Cache Redis** para queries pesadas (5 min)
- [ ] **Avoid N+1** queries

### 5. Observability

- [ ] **AuditLog** em ações críticas (APPROVE, REJECT, PUBLISH)
- [ ] **Logging estruturado**: `logger.info()` com contexto
- [ ] **Error tracking**: Try/except com logs

### 6. Accessibility (WCAG 2.0)

- [ ] **HTML semântico**: `<form>`, `<button>`, não `<div onclick>`
- [ ] **ARIA labels**: Em forms complexos
- [ ] **Keyboard navigation**: Full support
- [ ] **Color contrast**: Ratios suficientes

### 7. Testing

- [ ] **Behavior, not implementation** (testar o QUE faz)
- [ ] **3rd person verbs** (creates, approves, rejects)
- [ ] **Fixtures** para dados de teste
- [ ] **Coverage 90%+** (crítico: 100%)
- [ ] **Organization**: TestClass > TestSubRequirement > test_specific_behavior

### 8. Compliance Checks (aprender-domain)

#### Cláusulas Pétreas (CP-01 to CP-05)
- [ ] **CP-01**: Feature runs ONLY in Docker
- [ ] **CP-02**: If approval flow → PA-01 to PA-07 compliant
- [ ] **CP-03**: If availability → RD-01 to RD-08 compliant
- [ ] **CP-04**: Workflow followed (Understand → Plan → Implement → Test)
- [ ] **CP-05**: Conventional commits (`feat: ...` or `fix: ...`)

#### Regras de Disponibilidade (RD-01 to RD-08)
Se o código lida com disponibilidade/conflitos:
- [ ] **RD-01**: Non-overlapping (fim==início OK)
- [ ] **RD-02**: Total block (T) prevents any event
- [ ] **RD-03**: Partial block (P) prevents subinterval
- [ ] **RD-04**: Travel buffer (D) between cities
- [ ] **RD-05**: Daily capacity (M)
- [ ] **RD-06**: Timezone-aware (America/Fortaleza)
- [ ] **RD-07**: Priority: Blocks → Conflicts → Buffer → Capacity
- [ ] **RD-08**: Structured messages (code, title, detail, ref_id)

#### Política de Aprovação (PA-01 to PA-07)
Se o código lida com aprovações:
- [ ] **PA-01**: No auto-approval for SUPER projects
- [ ] **PA-02**: Only Superintendência can approve/reject
- [ ] **PA-03**: External integrations AFTER approval
- [ ] **PA-04**: Initial status = 'pendente' (SUPER)
- [ ] **PA-05**: AuditLog persistent (usuario, action, details, ip)
- [ ] **PA-06**: UI buttons hidden for non-authorized
- [ ] **PA-07**: 5 mandatory tests passing

### 9. Output Format

**For each issue found, provide**:
- **File:line**: Exact location
- **Issue**: Clear description
- **Rule**: Reference (e.g., CLAUDE-principles.md:L89, PA-02, RD-06)
- **Suggestion**: Code fix or refactoring
- **Severity**: CRITICAL (security/data loss), HIGH (compliance), MEDIUM (quality), LOW (style)

**Example**:
```
apps/core/views.py:145
Issue: Missing AuditLog for approval action
Rule: PA-05 (aprender-domain SKILL.md)
Suggestion: Add AuditLog.objects.create(usuario=request.user, action='APPROVE', ...)
Severity: HIGH
```

### 10. Final Summary

Provide:
- **Total issues**: Count by severity
- **Compliance status**: CP/RD/PA (PASS/FAIL with details)
- **Code quality score**: Type-safety, naming, testing, security (0-100)
- **Top 3 priorities**: Most critical fixes

## Reference

- **Code Quality**: `.claude/CLAUDE-principles.md`
- **Business Rules**: `.claude/skills/aprender-domain/SKILL.md`
- **Django Patterns**: `.claude/skills/django-patterns/SKILL.md` (when created)
- **Main Context**: `.claude/CLAUDE.md` (1.432 linhas)

---

**Focus**: Identify compliance gaps, security issues, and quality improvements with actionable suggestions.
