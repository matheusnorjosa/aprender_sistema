---
description: Plan and implement a new feature following Django/DRF best practices with focus on CP-01 to CP-06, RD, PA, and RF compliance
argument-hint: [feature description]
---

# New Feature Development (AS v2)

Plan and implement a new feature: $ARGUMENTS

## Approach:

### 1. Research & Analysis
- Analyze existing Django apps (`apps/core`, `apps/dat_ingest`)
- Identify model dependencies and migrations needed
- Review similar implementations in PR history (PR1-PR42)
- Check for CP/RD/PA/RF compliance requirements

### 2. Planning & Design
- Break down into manageable tasks (use TodoWrite)
- Design models (SSOT, constraints, FKs)
  - Models = Single Source of Truth
  - Constraints in DB (CHECK, UNIQUE, FK)
  - Timezone-aware (America/Fortaleza, store UTC)
- Plan serializers (read vs write separation)
- Consider RBAC (permission classes: `IsSuperintendencia`, etc.)
- Validate against Cláusulas Pétreas (CP-01 to CP-06)

### 3. Implementation Guidelines

#### Clarity (CLAUDE-principles.md)
- **Descriptive names**: `solicitacao_aprovada` > `data_list`
- **Avoid vague terms**: No `data`, `info`, `manager`, `helper`
- **Specific**: `municipio_origem` > `origin`

#### Python/Django
- **PEP8** + type hints obrigatórios
- **Early returns** (código flat, max 2-3 níveis indentação)
- **Services layer** para business logic (não em views)
- **Models**: Constraints no DB, índices, related_name

#### DRF
- **ViewSets** para CRUD padrão
- **Serializers**: Separar read/write
- **Permissions**: RBAC classes (`IsSuperintendencia`, `IsControleOrSuper`)
- **Throttling**: Para endpoints sensíveis

### 4. Core Implementation Focus

#### Type Safety
- **Type hints** em todos os services
- **DRF serializers** com validação
- **Django ORM** (nunca raw SQL)

#### Observability
- **AuditLog** para ações críticas (PA-05)
- **Logging estruturado**: `logger.info()` com contexto
- **Sentry**: Error tracking (futuro)

#### Security (OWASP)
- **CSRF**: Token em forms POST/PUT/DELETE
- **SQL Injection**: ORM obrigatório
- **Secrets**: Via `.env`, nunca hardcoded
- **RBAC**: Permissions verificadas

#### Accessibility (WCAG 2.0)
- **HTML semântico**: `<form>`, `<button>`, não `<div onclick>`
- **ARIA labels**: Em forms complexos
- **Keyboard navigation**: Full support

#### Performance
- **select_related/prefetch**: Para FKs e M2M
- **Índices DB**: Campos de filtro/ordenação
- **Cache Redis**: 5 min para monthly grid
- **Avoid N+1**: Usar prefetch

### 5. Testing Strategy

#### pytest
- **Behavior, not implementation**: Testar o QUE faz
- **3rd person verbs**: "creates AuditLog" (não "should create")
- **Fixtures**: Dados de teste reutilizáveis
- **Coverage**: 90%+ (crítico: 100%)

#### Test Organization
```python
class TestFeatureName:
    """Feature description"""

    class TestRequirement1:
        """Sub-requirement description"""
        def test_specific_behavior(self):
            ...
```

### 6. Compliance Checks

#### Cláusulas Pétreas (CP-01 to CP-05)
- [ ] **CP-01**: Feature runs ONLY in Docker
- [ ] **CP-02**: If approval flow → PA-01 to PA-07 compliant
- [ ] **CP-03**: If availability → RD-01 to RD-08 compliant
- [ ] **CP-04**: Workflow followed (Understand → Plan → Implement → Test)
- [ ] **CP-05**: Conventional commits (`feat: ...` or `fix: ...`)

#### Regras de Disponibilidade (RD-01 to RD-08)
- [ ] **RD-01**: Non-overlapping (fim==início OK)
- [ ] **RD-02**: Total block (T) prevents any event
- [ ] **RD-03**: Partial block (P) prevents subinterval
- [ ] **RD-04**: Travel buffer (D) between cities
- [ ] **RD-05**: Daily capacity (M)
- [ ] **RD-06**: Timezone-aware (America/Fortaleza)
- [ ] **RD-07**: Priority: Blocks → Conflicts → Buffer → Capacity
- [ ] **RD-08**: Structured messages (code, title, detail, ref_id)

#### Política de Aprovação (PA-01 to PA-07)
- [ ] **PA-01**: No auto-approval for SUPER projects
- [ ] **PA-02**: Only Superintendência can approve/reject
- [ ] **PA-03**: External integrations AFTER approval
- [ ] **PA-04**: Initial status = 'pendente' (SUPER)
- [ ] **PA-05**: AuditLog persistent (usuario, action, details, ip)
- [ ] **PA-06**: UI buttons hidden for non-authorized
- [ ] **PA-07**: 5 mandatory tests passing

### 7. Code Quality (CLAUDE-principles.md)

- [ ] **Type hints** em todas as funções
- [ ] **Naming descritivo** (sem vagos)
- [ ] **Early returns** (código flat)
- [ ] **Comments** convertidos para funções/variáveis (98%)
- [ ] **DRY**: Código não repetido
- [ ] **Services**: Business logic fora de views
- [ ] **PEP8**: flake8 sem erros

### 8. Final Checks

- [ ] **Migrations**: `make migrate` executado
- [ ] **Tests**: `pytest -v` passando (90%+)
- [ ] **RBAC**: Permissions verificadas
- [ ] **AuditLog**: Ações críticas logadas
- [ ] **CP/RD/PA**: Compliance validado
- [ ] **Git**: Conventional commit (`feat(v2): ...`)
- [ ] **Documentation**: CLAUDE.md atualizado (se necessário)

## Reference

- **Business Rules**: `.claude/skills/aprender-domain/SKILL.md` (CP, RD, PA, RF)
- **Django Patterns**: `.claude/skills/django-patterns/SKILL.md`
- **Code Quality**: `.claude/CLAUDE-principles.md`
- **Main Context**: `.claude/CLAUDE.md` (1.432 linhas)

---

**Focus**: Clear, observable, secure, accessible, performant code that follows AS v2 established patterns.
