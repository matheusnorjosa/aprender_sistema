# Princípios de Qualidade de Código — AS v2

**Complemento ao CLAUDE.md principal**
**Baseado em: Configuração Premium Claude Code (TypeScript/React adaptado para Python/Django)**

---

## 🎯 Como Usar Este Arquivo

- **CLAUDE.md**: Contém TODAS as regras de negócio do AS v2 (CP, RD, PA, RF, histórico de PRs)
- **Este arquivo**: Contém princípios de QUALIDADE DE CÓDIGO aplicáveis a qualquer implementação
- **Use ambos**: CLAUDE.md para regras de negócio + este para qualidade de código

---

## 🚫 Git Workflow

- **Não incluir "Claude Code" em commit messages** (configurado em `settings.json`: `includeCoAuthoredBy=false`)
- **Use conventional commits**: `<type>(<scope>): <message>` (já definido em CP-06)

---

## 🧠 Karpathy Principles (Reduzir Erros Comuns de LLM)

**Baseado em: forrestchang/andrej-karpathy-skills**
Aplicar em TODA interação. Viés para cautela sobre velocidade.

### 1. Think Before Coding

**Não assuma. Não esconda confusão. Superfície tradeoffs.**

Antes de implementar:

- Declare suas premissas explicitamente. Se incerto, pergunte.
- Se há múltiplas interpretações, apresente-as — não escolha silenciosamente.
- Se há abordagem mais simples, diga. Push back quando justificado.
- Se algo não está claro, pare. Nomeie o que confunde. Pergunte.

### 2. Simplicity First

**Código mínimo que resolve o problema. Nada especulativo.**

- Sem features além do pedido.
- Sem abstrações para código usado 1x.
- Sem "flexibilidade" que não foi pedida.
- Sem error handling para cenários impossíveis.
- Se escreveu 200 linhas e dava pra fazer em 50, reescreve.

Pergunte: "Um senior engineer diria que isto está super-complicado?" Se sim, simplifique.

### 3. Surgical Changes

**Toque só no que é necessário. Limpe só a sua própria bagunça.**

Ao editar código existente:

- Não "melhore" código, comentários ou formatação adjacentes.
- Não refatore coisas que não estão quebradas.
- Siga o estilo existente, mesmo que você faria diferente.
- Se notar dead code não relacionado, mencione — não delete.

Quando suas mudanças criam órfãos:

- Remova imports/variáveis que SUAS mudanças tornaram inúteis.
- Não remova dead code pré-existente a menos que pedido.

**Teste:** Cada linha alterada deve rastrear diretamente ao pedido do usuário.

### 4. Goal-Driven Execution

**Defina critérios de sucesso. Loop até verificado.**

Transforme tarefas em objetivos verificáveis:

- "Adicionar validação" → "Escrever testes para inputs inválidos, depois fazê-los passar"
- "Corrigir o bug" → "Escrever teste que reproduz, depois fazê-lo passar"
- "Refatorar X" → "Garantir testes passam antes e depois"

Para tarefas multi-step, declare plano breve:

```text
1. [Passo] → verificar: [check]
2. [Passo] → verificar: [check]
3. [Passo] → verificar: [check]
```

Critérios fortes permitem loop independente. Fracos ("faça funcionar") geram ida-e-volta.

---

**Estes princípios funcionam se:** menos mudanças desnecessárias em diffs, menos rewrites por super-engineering, perguntas de clarificação ANTES da implementação em vez de depois dos erros.

---

## 🎯 Foco Principal (Aplicar em TODO Código)

### 1. Type-Safety (e2e: API → Database)

**Goal**: End-to-end type-safety from API requests to database queries.

#### Python Type Hints (Pyright Strict)
- **Obrigatório** em todas as functions/methods
- **PEP 695** type aliases (Python 3.12+)
- **Pyright strict mode**: Zero errors allowed
- **Never use `Any`** without documented justification

**Example**:
```python
# PEP 695: Modern type aliases
type UserId = int
type Status = Literal["pendente", "aprovado", "reprovado"]

def check_conflicts(
    usuario: Usuario,
    inicio: datetime,
    fim: datetime,
    municipio: Municipio
) -> AvailabilityResult:
    """Check conflicts with full type safety."""
```

#### Django ORM Typed
- **QuerySet with Self**: Type-safe queries
- **No raw SQL**: ORM protects against SQL injection
- **select_related/prefetch_related**: Typed chains

**Example**:
```python
from typing import Self
from django.db import models

class SolicitacaoQuerySet(models.QuerySet["Solicitacao"]):
    def pendentes(self) -> Self:
        return self.filter(status="pendente")

    def aprovadas(self) -> Self:
        return self.filter(status="aprovado")

class Solicitacao(models.Model):
    objects = SolicitacaoQuerySet.as_manager()
```

#### DRF Serializers Typed
- **Serializers with generics**: Type-safe validation
- **Explicit field types**: No `__all__` in production
- **Custom validation**: Typed methods

**Example**:
```python
from rest_framework import serializers

class SolicitacaoSerializer(serializers.ModelSerializer[Solicitacao]):
    municipio = serializers.PrimaryKeyRelatedField(
        queryset=Municipio.objects.filter(ativo=True)
    )

    def validate_fim(self, value: datetime) -> datetime:
        if value <= self.initial_data.get('inicio'):
            raise serializers.ValidationError("fim must be > inicio")
        return value

    class Meta:
        model = Solicitacao
        fields = ['id', 'projeto', 'municipio', 'inicio', 'fim', 'status']
```

#### Type Safety Checklist
- [ ] Type hints on all public functions/methods
- [ ] PEP 695 aliases for complex types
- [ ] Pyright strict mode passing (0 errors)
- [ ] Django QuerySet typed with `Self`
- [ ] DRF Serializers with `ModelSerializer[Model]`
- [ ] No `Any` usage (or documented exceptions)
- [ ] CI blocks PRs with type errors

**Why e2e type-safety matters**:
- Catches errors at dev time (not runtime/production)
- Autocomplete 3x better (95% vs 30% accuracy)
- Refactoring safe (IDE detects breakages)
- Self-documenting code (type hints never outdated)

### 2. Observability
- **AuditLog**: Todas as ações críticas (APPROVE, REJECT, PUBLISH)
- **Logging estruturado**: `logger.info()` com contexto claro
- **Sentry**: Error tracking (futuro, já planejado)

### 3. Automated Tests
- **Coverage**: 85%+ (crítico: 100% em `availability_service`, `solicitacao_approval`)
- **Behavior, not implementation**: Testar o QUE faz, não COMO faz
- **3rd person verbs**: "creates AuditLog" (não "should create")
- **pytest**: Fixtures para dados de teste

### 4. Readability/Maintainability
- **PEP8**: Estilo Python padrão
- **Early returns**: Evitar if-else aninhados
- **Código flat**: Evitar indentação profunda (max 2-3 níveis)
- **1 função = 1 propósito**: Single Responsibility Principle

### 5. Security (OWASP)
- **CSRF Protection**: Token em todos os forms POST/PUT/DELETE
- **SQL Injection**: ORM obrigatório (não raw SQL)
- **Secrets**: Via `.env`, nunca hardcoded
- **RBAC**: DRF permission classes via `permission_classes=[HasPerm("codename")]` (`apps.core.rbac`); composition `HasPerm("a")|HasPerm("b")`. Classes legacy (`IsSuperintendencia`) e `user.groups.filter(name=...)` são banidas por `scripts/rbac_lint.py`.

### 6. Accessibility (WCAG 2.0)
- **Templates HTML**: Semantic HTML5
- **ARIA labels**: Em forms e buttons
- **Keyboard navigation**: Full support
- **Color contrast**: Sufficient ratios

---

## ✍️ Naming Conventions (ABSOLUTO)

### Python/Django
| Elemento | Convenção | Exemplo |
|----------|-----------|---------|
| **Models/Classes** | `UpperCamelCase` | `Usuario`, `Solicitacao` |
| **Functions/Methods** | `snake_case` | `check_conflicts`, `apply_one` |
| **Constants** | `SNAKE_CAPS` | `IMPORT_MAX_DUPLICATES_PCT` |
| **Files** | `snake_case.py` | `availability_service.py` |
| **Model Fields** | `snake_case` | `data_entrega`, `gcal_status` |

### Descriptive Names (Specific, Not Vague)
✅ **GOOD**:
- `usuario_aprovador` (não `user` ou `approver_data`)
- `solicitacao_pendente` (não `pending_item`)
- `municipio_origem` (não `origin`)
- `retry_count_max` (não `max_retries` ou `maximumNumberOfRetries`)

❌ **AVOID**:
- Termos vagos: `data`, `info`, `list`, `manager`, `helper`, `stuff`
- Prefixos/sufixos desnecessários: `UserManager`, `DataHelper`, `InfoService`
- Redundância: `userList` → `users`, `dataObject` → `data` (contexto já define)

### Examples

**❌ Ruim:**
```python
def process_data(data):  # Vago: qual data? qual processo?
    info = data.get('info')  # Vago: qual informação?
    manager = DataManager()  # Sufixo desnecessário
    return manager.handle(info)
```

**✅ Bom:**
```python
def approve_solicitacao(solicitacao: Solicitacao) -> Aprovacao:
    aprovador = solicitacao.solicitante
    audit_service = AuditLogService()  # Service é OK quando realmente é serviço
    return audit_service.log_approval(solicitacao, aprovador)
```

---

## 📐 Code Organization

### Single Responsibility
- **1 função = 1 propósito**
- **DRY**: Não repetir código (extrair para funções)
- **Services Layer**: Lógica de negócio fora das views
  ```
  views.py → chama → services/ → chama → models.py
  ```

### Keep Code Close
- **Usado 1x**: Inline ou próximo ao uso
- **Usado 2-3x**: Extrair para função no mesmo arquivo
- **Usado 4+x**: Extrair para módulo separado (utils, services)

### Avoid Useless Abstractions
❌ **Ruim:**
```python
def get_usuario(id):
    return Usuario.objects.get(id=id)  # Helper usado 1x = inútil
```

✅ **Bom:**
```python
# Usar diretamente onde necessário
usuario = Usuario.objects.get(id=usuario_id)
```

### A Folder with Single File Should Be a Single File
❌ **Ruim:**
```
services/
└── solicitacao_approval/
    └── __init__.py  # Único arquivo
```

✅ **Bom:**
```
services/
└── solicitacao_approval.py  # Direto
```

---

## 🔄 Control Flow

### Early Returns (SEMPRE)
❌ **Ruim:**
```python
def approve(solicitacao):
    if solicitacao.status == 'pendente':
        if user_has_any_perm(request.user, "aprovar_solicitacao"):
            # ... lógica de aprovação
            return success
        else:
            return error_permission
    else:
        return error_status
```

✅ **Bom:**
```python
def approve(solicitacao):
    # Early returns = código flat
    if solicitacao.status != 'pendente':
        return error_status

    if not user_has_any_perm(request.user, "aprovar_solicitacao"):
        return error_permission

    # Lógica principal no nível mais alto
    audit_log = AuditLog.objects.create(...)
    solicitacao.status = 'aprovado'
    solicitacao.save()
    return success
```

### Hash-Lists over Switch-Case
**Python 3.10+ tem `match/case`, mas prefira dict dispatch para casos simples:**

✅ **Bom:**
```python
CONFLICT_HANDLERS = {
    'T': handle_total_block,
    'P': handle_partial_block,
    'D': handle_travel_buffer,
    'M': handle_daily_capacity,
}

handler = CONFLICT_HANDLERS.get(conflict_code)
if handler:
    handler(solicitacao)
```

---

## 🧪 Testing Philosophy

### Behavior, Not Implementation
❌ **Ruim:**
```python
def test_approve_calls_save():
    """Test that approve() calls save()"""  # Testa implementação!
    mock_save = Mock()
    solicitacao.save = mock_save
    approve(solicitacao)
    assert mock_save.called
```

✅ **Bom:**
```python
def test_approve_creates_audit_log():
    """Approve creates AuditLog with action APPROVE."""  # Testa comportamento!
    approve(solicitacao)
    assert AuditLog.objects.filter(
        action='APPROVE',
        details__solicitacao_id=solicitacao.id
    ).exists()
```

### 3rd Person Verbs (Não "should")
❌ **Ruim:**
```python
def test_should_create_event():  # "should" é vago
    ...
```

✅ **Bom:**
```python
def test_approve_creates_google_event():  # Verbo de ação direto
    ...

def test_reject_sends_notification_email():
    ...
```

### Describe Clauses for Organization
```python
class TestSolicitacaoApproval:
    """Approval flow tests (PA-01 to PA-07)"""

    class TestManualApproval:
        """PA-01: No auto-approval for SUPER projects"""
        def test_super_project_stays_pending(self):
            ...

        def test_nao_super_project_auto_approved(self):
            ...

    class TestPermissions:
        """PA-02: Only Superintendência can approve"""
        def test_superintendencia_approves_successfully(self):
            ...

        def test_coordenador_gets_403_forbidden(self):
            ...
```

---

## 💬 Comments (98% Desnecessários)

### Convert Comments to Functions/Variables
❌ **Ruim:**
```python
# Check if user has permission to approve
# NOTA: groups.filter(name=...) é BANIDO por scripts/rbac_lint.py fora da whitelist
if request.user.is_superuser or request.user.groups.filter(name='Superintendência').exists():
    ...
```

✅ **Bom:**
```python
from apps.core.rbac import user_has_any_perm

def can_approve_solicitacao(user: Usuario) -> bool:
    return user_has_any_perm(user, "aprovar_solicitacao")

if can_approve_solicitacao(request.user):
    ...
```

### When Comments ARE Useful
✅ **Docstrings** (obrigatórios):
```python
def check_conflicts(usuario, inicio, fim, municipio):
    """
    Verifica conflitos de disponibilidade seguindo RD-01 a RD-08.

    Args:
        usuario: Usuário a verificar
        inicio: Data/hora início (aware, America/Fortaleza)
        fim: Data/hora fim (aware, America/Fortaleza)
        municipio: Município do evento

    Returns:
        AvailabilityResult com lista de ConflictDetail

    Raises:
        ValueError: Se fim <= inicio
    """
```

✅ **WHY, não WHAT** (quando lógica é não-óbvia):
```python
# PA-03: Google Calendar integration only AFTER manual approval
# (Superintendência may override conflicts with human context)
if solicitacao.status == 'aprovado':
    task_publish_to_gcal.delay(solicitacao.id)
```

---

## 🔧 Django/DRF Patterns

### Models = SSOT
```python
class Solicitacao(models.Model):
    class Meta:
        constraints = [
            # Lógica de negócio NO BANCO (não só no Python)
            models.CheckConstraint(
                check=Q(fim__gt=F('inicio')),
                name='valid_time_range'
            )
        ]
        indexes = [
            models.Index(fields=['data', 'status'])
        ]
```

### Services for Business Logic
```
views.py        → Apenas orquestração (thin controllers)
↓
services/       → Business logic (check_conflicts, approve_workflow)
↓
models.py       → Data access (queries, save)
```

### Serializers: Read vs Write
```python
# Read (para GET) - StringRelatedField
class SolicitacaoReadSerializer(serializers.ModelSerializer):
    municipio = serializers.StringRelatedField()  # "Fortaleza-CE"

# Write (para POST/PUT) - PrimaryKeyRelatedField
class SolicitacaoWriteSerializer(serializers.ModelSerializer):
    municipio = serializers.PrimaryKeyRelatedField(
        queryset=Municipio.objects.filter(ativo=True)
    )

# ViewSet usa ambos
class SolicitacaoViewSet(viewsets.ModelViewSet):
    def get_serializer_class(self):
        if self.action in ['list', 'retrieve']:
            return SolicitacaoReadSerializer
        return SolicitacaoWriteSerializer
```

---

## ⚡ Performance

### Avoid Premature Optimization
- **Primeiro**: Código correto e legível
- **Depois**: Profile e otimize gargalos reais
- **Não otimize** sem medir primeiro

### Django ORM Optimization
✅ **GOOD**:
```python
# select_related para FKs (1:1, N:1)
solicitacoes = Solicitacao.objects.select_related(
    'municipio', 'projeto', 'solicitante'
)

# prefetch_related para M2M
solicitacoes = solicitacoes.prefetch_related('participacoes__usuario')

# Resultado: 3 queries em vez de N+1
```

❌ **BAD**:
```python
# N+1 queries!
for s in Solicitacao.objects.all():  # Query 1
    print(s.municipio.nome)  # Query 2, 3, 4, ...
```

### Cache Redis
```python
from django.core.cache import cache

def get_monthly_grid(year, month):
    cache_key = f'monthly_grid:{year}:{month}'
    result = cache.get(cache_key)

    if result is None:
        result = expensive_computation(year, month)
        cache.set(cache_key, result, timeout=300)  # 5 min

    return result
```

---

## ✍️ Writing Standards

### Core Principles (From Premium Package)

#### Be Concise
- Every word must earn its place
- Delete redundant words
- Short sentences convey ideas clearly (max 25 words)

#### Active Voice
- ✅ "We fixed the bug" / "The service validates"
- ❌ "The bug was fixed" / "Validation is performed"

#### One Idea Per Sentence
- Each sentence expresses one clear idea
- Complex ideas get multiple sentences
- Don't nest multiple concepts

#### Lead with Results
- Put the outcome first
- Make conclusions obvious
- Don't bury the lead

### Docstrings (PEP 257 Required)

**Python requires docstrings** for public functions/classes:

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
        AvailabilityResult with list of ConflictDetail instances

    Raises:
        ValueError: If fim <= inicio
    """
```

### Commit Messages (Conventional Commits)

```
<type>(<scope>): <message>

feat(core): add conflict detection service (RD-01 to RD-08)
fix(imports): handle empty CSV files gracefully
```

- Use imperative mood ("Add" not "Added")
- Be specific about what changed
- Max 72 characters for first line
- **Never include "Claude Code"**

### Error Messages (User-Facing)

**Format**: `<What happened>. <What to do>.`

- ✅ `Solicitação not found. Check the ID and try again.`
- ✅ `Conflict detected (RD-02): Total block from 09:00 to 12:00.`
- ❌ `An error occurred.`
- ❌ `Something went wrong.`

### Writing Anti-Patterns

**Avoid**:
- Redundant words: "in order to" → "to"
- Weak verbs: "is able to" → "can"
- Passive voice
- Hedging: "might", "possibly" (when you know)
- Jargon without explanation

**Watch for**:
- Long sentences (>25 words)
- Dense paragraphs (>5 sentences)
- Ambiguous pronouns ("it", "this" without clear referent)

---

## 🔗 When to Use What Skill

| Task | Use Skill | Why |
|------|-----------|-----|
| Implementar RF/RD/PA | `aprender-domain` | Regras de negócio AS v2 |
| Criar model/ViewSet | `django-patterns` | Padrões Django/DRF |
| Importar dados | `import_export_contract` (mgmt cmd) + endpoints DRF | ETL legado REMOVIDO; ver `v2/docs/specs/backend/imports.spec.md` (`etl-guidelines` DEPRECADA) |
| Escrever docs/commits/PRs | `writing-standards` | Clareza, concisão, PEP 257 |
| Aplicar princípios qualidade | Este arquivo | Type-safety, naming, testing |

---

## 📚 Relationship with Other Files

```
.claude/
├── CLAUDE.md                    # REGRAS DE NEGÓCIO (CP, RD, PA, RF, histórico)
├── CLAUDE-principles.md         # QUALIDADE DE CÓDIGO (este arquivo)
├── skills/
│   ├── aprender-domain/         # Detalhes RD, PA, RF
│   ├── django-patterns/         # Implementação Django/DRF
│   └── etl-guidelines/          # DEPRECADA — ETL legado removido; ver v2/docs/specs/backend/imports.spec.md
└── commands/
    ├── /create-feature         # Usa: CLAUDE.md + principles + django-patterns
    ├── /review-enhanced        # Usa: principles + aprender-domain
    └── /check-conflicts         # Usa: aprender-domain (RD-01 to RD-08)
```

---

## ✅ Quick Checklist (Antes de Commitar)

- [ ] **Type hints** em todas as funções/métodos
- [ ] **Naming descritivo** (sem `data`, `info`, `manager` desnecessários)
- [ ] **Early returns** (código flat, sem if-else aninhados)
- [ ] **Testes** (behavior, 3rd person verbs, 85%+ coverage)
- [ ] **Comments** convertidos para funções/variáveis (98% dos casos)
- [ ] **PEP8** (flake8 sem erros)
- [ ] **RBAC** verificado (permissions corretas)
- [ ] **AuditLog** em ações críticas
- [ ] **ORM** (sem raw SQL)
- [ ] **Conventional commits** (feat/fix/chore: message)

---

**Última Atualização**: 2026-06
**Versão**: 1.0 (Adaptado de Configuração Premium)
**Complementa**: CLAUDE.md (regras de negócio AS v2)
