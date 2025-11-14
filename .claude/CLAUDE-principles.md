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

## 🎯 Foco Principal (Aplicar em TODO Código)

### 1. Type-Safety
- **Python**: Type hints obrigatórios em functions/methods
  ```python
  def check_conflicts(
      usuario: Usuario,
      inicio: datetime,
      fim: datetime,
      municipio: Municipio
  ) -> AvailabilityResult:
  ```
- **DRF**: Serializers com validação explícita
- **Django ORM**: Nunca raw SQL (proteção SQL injection)

### 2. Observability
- **AuditLog**: Todas as ações críticas (APPROVE, REJECT, PUBLISH)
- **Logging estruturado**: `logger.info()` com contexto claro
- **Sentry**: Error tracking (futuro, já planejado)

### 3. Automated Tests
- **Coverage**: 90%+ (crítico: 100% em `availability_service`, `approval_workflow`)
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
- **RBAC**: Permissions classes (`IsSuperintendencia`, etc.)

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
| **Constants** | `SNAKE_CAPS` | `ETL_MAX_DUPLICATES_PCT` |
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
└── approval_service/
    └── __init__.py  # Único arquivo
```

✅ **Bom:**
```
services/
└── approval_service.py  # Direto
```

---

## 🔄 Control Flow

### Early Returns (SEMPRE)
❌ **Ruim:**
```python
def approve(solicitacao):
    if solicitacao.status == 'pendente':
        if request.user.is_superintendencia:
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

    if not request.user.is_superintendencia:
        return error_permission

    # Lógica principal no nível mais alto
    audit_log = AuditLog.objects.create(...)
    solicitacao.status = 'aprovado'
    solicitacao.save()
    return success
```

### Hash-Lists over Switch-Case
**Python não tem switch-case (até 3.9), mas se tiver:**

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
if request.user.is_superuser or request.user.groups.filter(name='Superintendência').exists():
    ...
```

✅ **Bom:**
```python
def can_approve_solicitacao(user: Usuario) -> bool:
    return user.is_superuser or user.groups.filter(name='Superintendência').exists()

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

## 🔗 When to Use What Skill

| Task | Use Skill | Why |
|------|-----------|-----|
| Implementar RF/RD/PA | `aprender-domain` | Regras de negócio AS v2 |
| Criar model/ViewSet | `django-patterns` | Padrões Django/DRF |
| Implementar ETL | `etl-guidelines` | Idempotência, quality gates |
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
│   └── etl-guidelines/          # ETL idempotência
└── commands/
    ├── /new-feat                # Usa: CLAUDE.md + principles + django-patterns
    ├── /review                  # Usa: principles + aprender-domain
    └── /check-conflicts         # Usa: aprender-domain (RD-01 to RD-08)
```

---

## ✅ Quick Checklist (Antes de Commitar)

- [ ] **Type hints** em todas as funções/métodos
- [ ] **Naming descritivo** (sem `data`, `info`, `manager` desnecessários)
- [ ] **Early returns** (código flat, sem if-else aninhados)
- [ ] **Testes** (behavior, 3rd person verbs, 90%+ coverage)
- [ ] **Comments** convertidos para funções/variáveis (98% dos casos)
- [ ] **PEP8** (flake8 sem erros)
- [ ] **RBAC** verificado (permissions corretas)
- [ ] **AuditLog** em ações críticas
- [ ] **ORM** (sem raw SQL)
- [ ] **Conventional commits** (feat/fix/chore: message)

---

**Última Atualização**: 04/11/2025
**Versão**: 1.0 (Adaptado de Configuração Premium)
**Complementa**: CLAUDE.md (1.432 linhas de regras AS v2)
