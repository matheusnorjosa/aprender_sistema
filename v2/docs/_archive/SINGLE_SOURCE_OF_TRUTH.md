# 🎯 Single Source of Truth (SSOT) — AS v2

**Princípio Fundamental**: Cada dado tem **um único local autoritativo** no sistema.

---

## 🚨 Problema que Resolve

### Cenário Anterior (Planilhas)

```
Usuários.xlsx → Nome: "João Silva"
              → Email: "joao@example.com"

Agenda 2025.xlsx → Referência: =IMPORTRANGE("USR[Nome]")
                 → Risco: Dessincronia se Usuários.xlsx mudar

Controle 2025.xlsx → Cópia manual do nome
                   → Risco: Divergência de dados
```

**Problemas identificados**:
- ❌ Dados duplicados em 4 planilhas diferentes
- ❌ IMPORTRANGE = latência + falha de autenticação
- ❌ Inconsistências (nome "João Silva" vs "Joao Silva" vs "J. Silva")
- ❌ Sem validação de integridade (email inválido passa silenciosamente)

### Solução AS v2

```
PostgreSQL → core_usuario (PK: id, UK: email)
           ↑
           └── Única fonte de verdade
           └── ForeignKeys garantem integridade referencial
           └── Constraints validam dados na entrada
```

**Ganhos**:
- ✅ Dados centralizados em PostgreSQL
- ✅ ForeignKeys = impossível referenciar usuário inexistente
- ✅ Constraints = validação automática (email único, CPF válido)
- ✅ Performance = índices B-tree vs. busca linear em planilhas

---

## 📋 Regras SSOT por Entidade

### 1. **Usuario**

**Tabela**: `core_usuario`
**SSOT**: Nome, Email, CPF, Perfil

| Campo | Tipo | Constraint | Justificativa |
|-------|------|------------|---------------|
| `id` | Serial | PRIMARY KEY | Identificador único imutável |
| `nome` | VARCHAR(200) | NOT NULL, INDEX | Buscas por nome (autocomplete) |
| `email` | VARCHAR(254) | UNIQUE, NOT NULL | Autenticação, notificações |
| `cpf` | VARCHAR(14) | UNIQUE, CHECK(valid_cpf) | Identificação legal (LGPD) |
| `perfil` | VARCHAR(50) | CHECK IN (...) | RBAC (coordenador, superintendência, etc.) |

**Dependentes**:
- `core_formador.usuario_id` → FK (ON DELETE PROTECT)
- `core_solicitacao.solicitante_id` → FK (ON DELETE PROTECT)
- `core_aprovacao.aprovador_id` → FK (ON DELETE PROTECT)

**Validações Django**:
```python
class Usuario(models.Model):
    email = models.EmailField(unique=True, validators=[EmailValidator()])
    cpf = models.CharField(
        max_length=14,
        unique=True,
        validators=[validate_cpf]  # Custom validator
    )

    class Meta:
        constraints = [
            models.CheckConstraint(
                check=models.Q(perfil__in=['coordenador', 'superintendencia', 'formador', 'diretoria']),
                name='valid_perfil'
            )
        ]
```

### 2. **Formador**

**Tabela**: `core_formador`
**SSOT**: Área de Atuação, Status Ativo

| Campo | Tipo | Constraint | Justificativa |
|-------|------|------------|---------------|
| `id` | Serial | PRIMARY KEY | Identificador único |
| `usuario_id` | Integer | FK(Usuario), UNIQUE | 1:1 com Usuario |
| `area_atuacao` | VARCHAR(100) | NOT NULL | Filtragem de formadores qualificados |
| `ativo` | Boolean | DEFAULT TRUE | Soft delete (manter histórico) |

**Dependentes**:
- `core_solicitacao_formadores` → M2M
- `core_disponibilidade_formador` → FK
- `core_deslocamento` → FK

**Validações**:
```python
class Formador(models.Model):
    usuario = models.OneToOneField(
        Usuario,
        on_delete=models.PROTECT,  # Não permitir deletar Usuario com Formador vinculado
        related_name='formador'
    )

    def delete(self, *args, **kwargs):
        # Soft delete: apenas desativa
        self.ativo = False
        self.save()
```

### 3. **Solicitacao**

**Tabela**: `core_solicitacao`
**SSOT**: Dados do evento solicitado

| Campo | Tipo | Constraint | Justificativa |
|-------|------|------------|---------------|
| `id` | Serial | PRIMARY KEY | - |
| `solicitante_id` | Integer | FK(Usuario) | Rastreabilidade |
| `data` | Date | NOT NULL, INDEX | Queries por período |
| `hora_inicio` | Time | NOT NULL | Validação de conflitos |
| `hora_fim` | Time | NOT NULL, CHECK(>hora_inicio) | Lógica de negócio |
| `municipio_id` | Integer | FK(Municipio) | Buffer de deslocamento |
| `projeto_id` | Integer | FK(Projeto) | Agrupamento de métricas |
| `tipo_evento_id` | Integer | FK(TipoEvento) | Classificação |
| `status` | VARCHAR(20) | CHECK IN (...) | Workflow de aprovação |

**M2M**:
- `solicitacao_formadores` → Tabela intermediária com FKs

**Validações**:
```python
class Solicitacao(models.Model):
    formadores = models.ManyToManyField(Formador, related_name='solicitacoes')

    class Meta:
        constraints = [
            models.CheckConstraint(
                check=models.Q(hora_fim__gt=models.F('hora_inicio')),
                name='valid_time_range'
            ),
            models.CheckConstraint(
                check=models.Q(status__in=['PENDENTE', 'APROVADO', 'REPROVADO', 'CANCELADO']),
                name='valid_status'
            )
        ]
        indexes = [
            models.Index(fields=['data', 'status']),
            models.Index(fields=['solicitante', '-created_at']),
        ]
```

### 4. **Evento**

**Tabela**: `core_evento`
**SSOT**: Evento aprovado + integração Google Calendar

| Campo | Tipo | Constraint | Justificativa |
|-------|------|------------|---------------|
| `id` | Serial | PRIMARY KEY | - |
| `solicitacao_id` | Integer | FK(Solicitacao), UNIQUE | 1:1 após aprovação |
| `google_calendar_id` | VARCHAR(255) | UNIQUE, NULLABLE | ID do Google Calendar |
| `meet_link` | VARCHAR(500) | NULLABLE | Link gerado automaticamente |
| `criado_em` | Timestamp | AUTO | Auditoria |

**Regra de Negócio**:
- ✅ Evento só existe se `Solicitacao.status == 'APROVADO'`
- ✅ `google_calendar_id` preenchido após `create_google_event()` task Celery

**Validações**:
```python
class Evento(models.Model):
    solicitacao = models.OneToOneField(
        Solicitacao,
        on_delete=models.CASCADE,  # Deletar solicitação = deletar evento
        limit_choices_to={'status': 'APROVADO'}
    )

    def save(self, *args, **kwargs):
        if self.solicitacao.status != 'APROVADO':
            raise ValidationError('Evento só pode ser criado para solicitação aprovada')
        super().save(*args, **kwargs)
```

### 5. **DisponibilidadeFormador**

**Tabela**: `core_disponibilidade_formador`
**SSOT**: Bloqueios (Parcial/Total)

| Campo | Tipo | Constraint | Justificativa |
|-------|------|------------|---------------|
| `id` | Serial | PRIMARY KEY | - |
| `formador_id` | Integer | FK(Formador) | Dono do bloqueio |
| `data_inicial` | Date | NOT NULL | Range de bloqueio |
| `data_final` | Date | NOT NULL, CHECK(>=data_inicial) | - |
| `tipo` | CHAR(1) | CHECK IN ('P','T') | Parcial ou Total |
| `motivo` | TEXT | NULLABLE | Transparência |

**Índices**:
```sql
CREATE INDEX idx_disponibilidade_lookup ON core_disponibilidade_formador(
    formador_id,
    data_inicial,
    data_final
) WHERE tipo IN ('P', 'T');
```

**Validações**:
```python
class DisponibilidadeFormador(models.Model):
    TIPO_CHOICES = [
        ('P', 'Bloqueio Parcial'),
        ('T', 'Bloqueio Total'),
    ]
    tipo = models.CharField(max_length=1, choices=TIPO_CHOICES)

    class Meta:
        constraints = [
            models.CheckConstraint(
                check=models.Q(data_final__gte=models.F('data_inicial')),
                name='valid_date_range'
            )
        ]
```

### 6. **Municipio / Projeto / TipoEvento**

**Tabelas**: `core_municipio`, `core_projeto`, `core_tipo_evento`
**SSOT**: Dados mestres (seed data)

| Campo | Tipo | Constraint | Justificativa |
|-------|------|------------|---------------|
| `id` | Serial | PRIMARY KEY | - |
| `nome` | VARCHAR(200) | UNIQUE, NOT NULL | Identificador natural |
| `ativo` | Boolean | DEFAULT TRUE | Soft delete |

**Observação**: Estes modelos são **imutáveis** em produção (apenas Admin pode alterar).

---

## 🔗 Integridade Referencial

### Cascata de Deleção

| Relação | ON DELETE | Justificativa |
|---------|-----------|---------------|
| Usuario → Formador | **PROTECT** | Não permitir deletar usuário com formador vinculado |
| Formador → Solicitacao (M2M) | **PROTECT** | Manter histórico |
| Solicitacao → Evento | **CASCADE** | Evento não faz sentido sem solicitação |
| Solicitacao → Aprovacao | **CASCADE** | Aprovação é parte da solicitação |
| Formador → Disponibilidade | **CASCADE** | Bloqueio vinculado ao formador |

### Exemplo de Query com SSOT

❌ **Antes (Planilha com IMPORTRANGE)**:
```excel
=VLOOKUP(A2, IMPORTRANGE("USR_SHEET", "A:B"), 2, FALSE)
```
- Latência: ~500ms por célula
- Falha se planilha externa indisponível

✅ **Depois (Django ORM)**:
```python
solicitacao = Solicitacao.objects.select_related(
    'solicitante',
    'municipio',
    'projeto',
    'tipo_evento'
).prefetch_related('formadores').get(id=123)

print(solicitacao.solicitante.nome)        # 1 query (select_related)
print(solicitacao.formadores.all()[0].nome)  # 1 query (prefetch_related)
```
- Latência: ~5ms (índices PostgreSQL)
- Integridade garantida por FKs

---

## 🛡️ Validação em Camadas

### 1. **Database Layer** (PostgreSQL Constraints)

```sql
-- Exemplo: core_solicitacao
ALTER TABLE core_solicitacao
ADD CONSTRAINT chk_valid_time_range
CHECK (hora_fim > hora_inicio);

ALTER TABLE core_solicitacao
ADD CONSTRAINT chk_valid_status
CHECK (status IN ('PENDENTE', 'APROVADO', 'REPROVADO', 'CANCELADO'));
```

**Vantagens**:
- ✅ Impossível inserir dados inválidos (mesmo via SQL direto)
- ✅ Performance (validação no nível do BD)

### 2. **ORM Layer** (Django Model Constraints)

```python
class Solicitacao(models.Model):
    class Meta:
        constraints = [
            models.CheckConstraint(
                check=models.Q(hora_fim__gt=models.F('hora_inicio')),
                name='valid_time_range'
            )
        ]
```

**Vantagens**:
- ✅ Integração com migrations
- ✅ Erros Django nativos (mais amigáveis que PostgreSQL)

### 3. **Application Layer** (Forms/Serializers)

```python
class SolicitacaoForm(forms.ModelForm):
    def clean(self):
        cleaned_data = super().clean()
        hora_inicio = cleaned_data.get('hora_inicio')
        hora_fim = cleaned_data.get('hora_fim')

        if hora_inicio and hora_fim and hora_fim <= hora_inicio:
            raise ValidationError('Hora fim deve ser maior que hora início')

        # Validação de conflitos
        conflicts = ConflictChecker().check(cleaned_data)
        if conflicts:
            raise ValidationError(f'Conflitos: {conflicts}')

        return cleaned_data
```

**Vantagens**:
- ✅ Feedback antes de salvar no BD
- ✅ Mensagens customizadas para o usuário
- ✅ Validações complexas (ex: conflitos)

### 4. **UI Layer** (JavaScript Assíncrono)

```javascript
// Validação em tempo real (UX)
formadorSelect.addEventListener('change', async (e) => {
    const response = await fetch('/api/check-disponibilidade/', {
        method: 'POST',
        body: JSON.stringify({
            formador_id: e.target.value,
            data: dataInput.value
        })
    });

    const result = await response.json();
    if (!result.disponivel) {
        showWarning(`Formador indisponível: ${result.mensagem}`);
    }
});
```

**Vantagens**:
- ✅ Feedback instantâneo (antes de submeter)
- ✅ Melhor UX (ISO 9241-110: tolerância a erros)

---

## 📊 Auditoria de Mudanças (Django Simple History)

### Implementação

```python
from simple_history.models import HistoricalRecords

class Usuario(models.Model):
    nome = models.CharField(max_length=200)
    email = models.EmailField(unique=True)
    # ...
    history = HistoricalRecords()
```

**Resultado**: Tabela `core_usuario_history` com:
- Snapshot de cada versão do registro
- `history_date` (quando mudou)
- `history_user` (quem mudou)
- `history_type` (created/updated/deleted)

### Query de Histórico

```python
# Ver histórico completo de um usuário
usuario = Usuario.objects.get(email='joao@example.com')
for history in usuario.history.all():
    print(f"{history.history_date}: {history.nome} ({history.history_type})")

# Reverter para versão anterior
old_version = usuario.history.as_of(datetime(2025, 1, 1))
usuario.nome = old_version.nome
usuario.save()
```

---

## 🚫 Anti-Patterns a Evitar

### ❌ Duplicação de Dados

```python
# ERRADO: Duplicar email em duas tabelas
class Formador(models.Model):
    nome = models.CharField(max_length=200)  # ❌ Duplicado com Usuario
    email = models.EmailField()              # ❌ Duplicado com Usuario

# CERTO: ForeignKey para Usuario
class Formador(models.Model):
    usuario = models.OneToOneField(Usuario, on_delete=models.PROTECT)

    @property
    def nome(self):
        return self.usuario.nome

    @property
    def email(self):
        return self.usuario.email
```

### ❌ Dados Calculados Armazenados

```python
# ERRADO: Armazenar total de eventos (pode desatualizar)
class Formador(models.Model):
    total_eventos = models.IntegerField(default=0)  # ❌ Pode divergir

# CERTO: Property calculada ou Materialized View
class Formador(models.Model):
    @property
    def total_eventos(self):
        return self.solicitacoes.filter(status='APROVADO').count()

# OU: Materialized View para performance
# CREATE MATERIALIZED VIEW mv_formador_stats AS ...
```

### ❌ Validação Apenas no Frontend

```javascript
// ERRADO: Confiar apenas no JS (pode ser bypassado)
if (email.includes('@')) {  // ❌ Inseguro
    submitForm();
}
```

```python
# CERTO: Validação no backend (sempre)
class UsuarioForm(forms.ModelForm):
    def clean_email(self):
        email = self.cleaned_data.get('email')
        if not '@' in email:
            raise ValidationError('Email inválido')
        return email
```

---

## 📚 Checklist de Implementação

### Para Cada Modelo Django:

- [ ] **PK definida** (id Serial ou UUID)
- [ ] **Constraints de BD** (NOT NULL, UNIQUE, CHECK)
- [ ] **FKs configuradas** (on_delete apropriado)
- [ ] **Índices criados** (campos de busca/filtro)
- [ ] **Validações Django** (clean methods, validators)
- [ ] **Histórico ativado** (HistoricalRecords se crítico)
- [ ] **Tests unitários** (constraints, validações, queries)
- [ ] **Documentação** (docstrings, relacionamentos)

---

**Próximos Passos**: Implementar modelos conforme `MIGRATION_PLAN.md` → Fase 1.
