# 🧪 Testing Plan — AS v2

**Objetivo**: Garantir qualidade, confiabilidade e manutenibilidade do AS v2 através de uma estratégia de testes abrangente.

---

## 🎯 Filosofia de Testes

### Test-Driven Development (TDD)

**Ciclo Red-Green-Refactor**:
1. 🔴 **Red**: Escrever teste que falha
2. 🟢 **Green**: Implementar código mínimo para passar
3. 🔵 **Refactor**: Melhorar código mantendo testes passando

**Benefícios**:
- ✅ Design emergente (código testável = código bem estruturado)
- ✅ Documentação viva (testes mostram como usar o código)
- ✅ Confiança para refatorar (rede de segurança)

---

## 📊 Pirâmide de Testes

```
          /\
         /  \  E2E Tests (Playwright)           5%
        /    \  - Fluxos completos              - 10 cenários críticos
       /------\
      /        \  Integration Tests             15%
     /          \  - APIs, Views, DB            - 50 cenários
    /------------\
   /              \  Unit Tests                 80%
  /________________\  - Models, Services        - 200+ cenários
```

### Cobertura de Código

- **Mínimo aceitável**: 80%
- **Meta geral**: 90%+
- **Código crítico**: 100% (ConflictChecker, DisponibilidadeService, ApprovalWorkflow)

---

## 🧩 Unit Tests (80% dos testes)

### 1. Models

**Objetivo**: Testar validações, constraints, métodos custom.

#### Exemplo: `core/tests/test_models_usuario.py`

```python
import pytest
from django.core.exceptions import ValidationError
from core.models import Usuario, Formador

@pytest.mark.django_db
class TestUsuario:
    def test_criar_usuario_valido(self):
        usuario = Usuario.objects.create(
            nome='João Silva',
            email='joao@example.com',
            cpf='123.456.789-00',
            perfil='coordenador'
        )
        assert usuario.pk is not None
        assert usuario.nome == 'João Silva'

    def test_email_duplicado_deve_falhar(self):
        Usuario.objects.create(email='joao@example.com', nome='João')
        with pytest.raises(ValidationError):
            usuario2 = Usuario(email='joao@example.com', nome='Maria')
            usuario2.full_clean()  # Trigger validation

    def test_cpf_invalido_deve_falhar(self):
        with pytest.raises(ValidationError):
            usuario = Usuario(cpf='000.000.000-00', email='test@example.com')
            usuario.full_clean()

    def test_perfil_invalido_deve_falhar(self):
        with pytest.raises(ValidationError):
            usuario = Usuario(perfil='INVALID', email='test@example.com')
            usuario.full_clean()
```

#### Checklist: Models

- [ ] Todos os constraints testados (UNIQUE, NOT NULL, CHECK)
- [ ] Validações customizadas (validators)
- [ ] Métodos `clean()` e `save()` customizados
- [ ] Properties calculadas
- [ ] Relacionamentos (FKs, M2M)
- [ ] Soft delete (se aplicável)

### 2. Services (Lógica de Negócio)

**Objetivo**: Testar regras de negócio isoladamente.

#### Exemplo: `core/tests/test_conflict_checker.py`

```python
import pytest
from datetime import date, time
from core.services.conflict_checker import ConflictChecker
from core.models import Solicitacao, Formador, DisponibilidadeFormador

@pytest.mark.django_db
class TestConflictChecker:
    @pytest.fixture
    def formador(self):
        return Formador.objects.create(nome='João Silva')

    @pytest.fixture
    def checker(self):
        return ConflictChecker()

    def test_sobreposicao_total(self, formador, checker):
        # Evento A: 08:00-10:00
        Solicitacao.objects.create(
            formador=formador,
            data=date(2025, 10, 15),
            hora_inicio=time(8, 0),
            hora_fim=time(10, 0),
            status='APROVADO'
        )

        # Evento B: 09:00-11:00 → CONFLITO
        conflicts = checker.check(
            formador=formador,
            data=date(2025, 10, 15),
            hora_inicio=time(9, 0),
            hora_fim=time(11, 0)
        )

        assert len(conflicts) == 1
        assert 'SOBREPOSIÇÃO' in conflicts[0]

    def test_sem_conflito_bordas_adjacentes(self, formador, checker):
        # Evento A: 08:00-10:00
        Solicitacao.objects.create(
            formador=formador,
            data=date(2025, 10, 15),
            hora_inicio=time(8, 0),
            hora_fim=time(10, 0),
            status='APROVADO'
        )

        # Evento B: 10:00-12:00 → SEM CONFLITO (borda)
        conflicts = checker.check(
            formador=formador,
            data=date(2025, 10, 15),
            hora_inicio=time(10, 0),
            hora_fim=time(12, 0)
        )

        assert len(conflicts) == 0

    def test_bloqueio_total_impede_evento(self, formador, checker):
        # Bloqueio T: 01/10-31/10
        DisponibilidadeFormador.objects.create(
            formador=formador,
            data_inicial=date(2025, 10, 1),
            data_final=date(2025, 10, 31),
            tipo='T',
            motivo='Férias'
        )

        # Evento: 15/10 → CONFLITO
        conflicts = checker.check(
            formador=formador,
            data=date(2025, 10, 15),
            hora_inicio=time(9, 0),
            hora_fim=time(11, 0)
        )

        assert len(conflicts) == 1
        assert 'BLOQUEIO_TOTAL' in conflicts[0]

    def test_bloqueio_parcial_permite_fora_range(self, formador, checker):
        # Bloqueio P: 01/10-15/10
        DisponibilidadeFormador.objects.create(
            formador=formador,
            data_inicial=date(2025, 10, 1),
            data_final=date(2025, 10, 15),
            tipo='P',
            motivo='Disponibilidade reduzida'
        )

        # Evento: 20/10 (fora do range) → SEM CONFLITO
        conflicts = checker.check(
            formador=formador,
            data=date(2025, 10, 20),
            hora_inicio=time(9, 0),
            hora_fim=time(11, 0)
        )

        assert len(conflicts) == 0
```

#### Checklist: Services

- [ ] Cada método público tem testes
- [ ] Casos de sucesso (happy path)
- [ ] Casos de erro (edge cases)
- [ ] Validação de parâmetros
- [ ] Lógica condicional (todos os branches testados)
- [ ] Mocks para dependências externas

### 3. Forms & Serializers

**Objetivo**: Testar validação de entrada.

#### Exemplo: `core/tests/test_forms.py`

```python
import pytest
from core.forms import SolicitacaoForm

class TestSolicitacaoForm:
    def test_form_valido(self):
        form = SolicitacaoForm(data={
            'data': '15/10/2025',
            'hora_inicio': '09:00',
            'hora_fim': '11:00',
            'formadores': [1, 2],
            'municipio': 1,
            'projeto': 1,
            'tipo_evento': 1,
        })
        assert form.is_valid()

    def test_hora_fim_antes_inicio_deve_falhar(self):
        form = SolicitacaoForm(data={
            'data': '15/10/2025',
            'hora_inicio': '11:00',
            'hora_fim': '09:00',  # ERRO
            'formadores': [1],
        })
        assert not form.is_valid()
        assert 'hora_fim' in form.errors

    def test_sem_formadores_deve_falhar(self):
        form = SolicitacaoForm(data={
            'data': '15/10/2025',
            'hora_inicio': '09:00',
            'hora_fim': '11:00',
            'formadores': [],  # ERRO
        })
        assert not form.is_valid()
        assert 'formadores' in form.errors
```

---

## 🔗 Integration Tests (15% dos testes)

### 1. Views (Django Templates)

**Objetivo**: Testar fluxos completos backend → template → response.

#### Exemplo: `core/tests/test_views_solicitacao.py`

```python
import pytest
from django.test import Client
from django.urls import reverse
from core.models import Usuario, Solicitacao

@pytest.mark.django_db
class TestSolicitacaoViews:
    @pytest.fixture
    def client(self):
        return Client()

    @pytest.fixture
    def usuario_logado(self, client):
        usuario = Usuario.objects.create_user(
            username='coordenador',
            password='senha123',
            perfil='coordenador'
        )
        client.login(username='coordenador', password='senha123')
        return usuario

    def test_acessar_form_sem_login_redirect(self, client):
        response = client.get(reverse('core:solicitar_evento'))
        assert response.status_code == 302  # Redirect to login

    def test_criar_solicitacao_valida(self, client, usuario_logado):
        response = client.post(reverse('core:solicitar_evento'), {
            'data': '15/10/2025',
            'hora_inicio': '09:00',
            'hora_fim': '11:00',
            'formadores': [1, 2],
            'municipio': 1,
            'projeto': 1,
            'tipo_evento': 1,
        })
        assert response.status_code == 302  # Redirect após sucesso

        # Verificar que solicitação foi criada
        assert Solicitacao.objects.filter(
            solicitante=usuario_logado
        ).exists()

    def test_criar_solicitacao_com_conflito_mostra_erro(self, client, usuario_logado):
        # Criar evento existente
        Solicitacao.objects.create(
            solicitante=usuario_logado,
            data='15/10/2025',
            hora_inicio='09:00',
            hora_fim='11:00',
            status='APROVADO'
        )

        # Tentar criar evento sobreposto
        response = client.post(reverse('core:solicitar_evento'), {
            'data': '15/10/2025',
            'hora_inicio': '10:00',  # Sobrepõe
            'hora_fim': '12:00',
            'formadores': [1],
        })

        assert response.status_code == 200  # Form re-renderizado
        assert 'CONFLITO' in response.content.decode()
```

### 2. API Endpoints (DRF)

**Objetivo**: Testar endpoints REST.

#### Exemplo: `dat_ingest/tests/test_api.py`

```python
import pytest
from rest_framework.test import APIClient
from rest_framework import status
from core.models import Usuario

@pytest.mark.django_db
class TestIngestAPI:
    @pytest.fixture
    def api_client(self):
        client = APIClient()
        admin = Usuario.objects.create_superuser(
            username='admin',
            password='admin123'
        )
        client.force_authenticate(user=admin)
        return client

    def test_ingest_agenda_success(self, api_client):
        # Mock de arquivos CSV
        events_csv = b'external_hash,municipio,data,projeto\nABC123,Fortaleza,15/10/2025,Proj1'
        people_csv = b'row_hash,event_external_hash,role,name\nP123,ABC123,FORMADOR,João'

        response = api_client.post('/api/ingest/agenda/', {
            'events': SimpleUploadedFile('events.csv', events_csv),
            'people': SimpleUploadedFile('people.csv', people_csv),
        }, format='multipart')

        assert response.status_code == status.HTTP_200_OK
        assert response.data['events_upserted'] == 1
        assert response.data['people_upserted'] == 1

    def test_health_check_requires_auth(self):
        client = APIClient()  # Sem autenticação
        response = client.get('/api/ingest/health/')
        assert response.status_code == status.HTTP_403_FORBIDDEN
```

---

## 🌐 End-to-End Tests (5% dos testes)

### Objetivo

Testar fluxos completos como usuário real: browser → frontend → backend → DB → Google Calendar.

### Ferramenta

**Playwright MCP** (já configurado no projeto)

### Cenários Críticos

#### 1. **RF02 — Solicitar Evento Sem Conflito**

```python
# tests/e2e/test_solicitar_evento.py
import pytest
from playwright.sync_api import Page, expect

def test_solicitar_evento_sem_conflito(page: Page):
    # 1. Login como coordenador
    page.goto('http://localhost:8000/login/')
    page.fill('#id_username', 'coordenador')
    page.fill('#id_password', 'senha123')
    page.click('button[type="submit"]')

    # 2. Navegar para formulário
    page.click('text=Solicitar Evento')
    expect(page).to_have_url('http://localhost:8000/solicitar/')

    # 3. Preencher formulário
    page.fill('#id_data', '15/10/2025')
    page.select_option('#id_municipio', label='Fortaleza')
    page.select_option('#id_projeto', label='Alfabetização')
    page.select_option('#id_tipo_evento', label='Formação Inicial')
    page.fill('#id_hora_inicio', '09:00')
    page.fill('#id_hora_fim', '11:00')
    page.select_option('#id_formadores', label='João Silva')

    # 4. Submeter
    page.click('button[type="submit"]')

    # 5. Verificar sucesso
    expect(page.locator('.alert-success')).to_contain_text(
        'Solicitação criada com sucesso'
    )
```

#### 2. **RF03 — Detectar Conflito de Disponibilidade**

```python
def test_solicitar_evento_com_conflito_deve_falhar(page: Page):
    # Pre-condition: Evento já existe
    # ...

    page.goto('http://localhost:8000/solicitar/')
    page.fill('#id_data', '15/10/2025')
    page.select_option('#id_formadores', label='João Silva')
    # (mesmo horário de evento existente)
    page.click('button[type="submit"]')

    # Esperado: erro
    expect(page.locator('.alert-danger')).to_contain_text(
        'Conflito detectado'
    )
```

#### 3. **RF04 — Fluxo de Aprovação**

```python
def test_aprovar_solicitacao_cria_evento_google(page: Page):
    # 1. Login como superintendência
    page.goto('http://localhost:8000/login/')
    page.fill('#id_username', 'superintendente')
    page.fill('#id_password', 'senha123')
    page.click('button[type="submit"]')

    # 2. Navegar para aprovações pendentes
    page.click('text=Aprovações Pendentes')

    # 3. Aprovar primeira solicitação
    page.click('button[data-action="approve"][data-id="1"]')

    # 4. Aguardar task Celery (mock ou real)
    page.wait_for_selector('.alert-success')

    # 5. Verificar que evento foi criado
    expect(page.locator('.google-calendar-link')).to_be_visible()
```

#### 4. **RF08 — Mapa de Disponibilidade**

```python
def test_mapa_disponibilidade_carrega_corretamente(page: Page):
    page.goto('http://localhost:8000/disponibilidade/')

    # Selecionar formador
    page.select_option('#formador_select', label='João Silva')

    # Esperado: calendário renderizado
    calendar_days = page.locator('.calendar-day')
    expect(calendar_days).to_have_count(31)  # Outubro = 31 dias

    # Verificar cores (exemplo: dia 15 tem evento)
    day_15 = page.locator('.calendar-day[data-day="15"]')
    expect(day_15).to_have_class('status-E')  # E = Evento confirmado
```

### Checklist: E2E

- [ ] RF02 — Solicitar evento sem conflito
- [ ] RF03 — Detectar conflito e bloquear
- [ ] RF04 — Aprovar solicitação
- [ ] RF05 — Criar evento no Google Calendar
- [ ] RF06 — Gerar link do Google Meet
- [ ] RF07 — Auditoria de operações
- [ ] RF08 — Visualizar mapa de disponibilidade
- [ ] RF09 — Bloquear disponibilidade (P/T)
- [ ] RF10 — Registrar deslocamento (D)
- [ ] RF11 — Cancelar solicitação

---

## 🔒 Security Tests

### Objetivo

Garantir que AS v2 está protegido contra vulnerabilidades comuns.

### Ferramenta

- **Bandit**: Static analysis for Python
- **Django's security checklist**: `python manage.py check --deploy`

### Testes Automáticos

#### 1. SQL Injection

```python
def test_sql_injection_protegido():
    # Tentar injeção via query string
    response = client.get('/solicitacoes/?data=1; DROP TABLE core_solicitacao;')
    # Django ORM escapa automaticamente
    assert Solicitacao.objects.exists()  # Tabela não foi deletada
```

#### 2. XSS (Cross-Site Scripting)

```python
def test_xss_protegido():
    # Criar solicitação com script malicioso
    Solicitacao.objects.create(
        titulo='<script>alert("XSS")</script>',
        # ...
    )

    response = client.get('/solicitacoes/1/')
    # Templates Django escapam automaticamente
    assert '<script>' not in response.content.decode()
    assert '&lt;script&gt;' in response.content.decode()
```

#### 3. CSRF Protection

```python
def test_csrf_token_obrigatorio():
    # Tentar POST sem token CSRF
    client = Client(enforce_csrf_checks=True)
    response = client.post('/solicitar/', {
        'data': '15/10/2025',
        # ...
    })
    assert response.status_code == 403  # Forbidden
```

---

## 📊 Performance Tests

### Objetivo

Garantir que AS v2 atende SLAs de performance.

### Ferramenta

- **Locust**: Load testing

### Cenários

#### 1. Criar Solicitação (Carga)

```python
# locustfile.py
from locust import HttpUser, task, between

class SolicitacaoUser(HttpUser):
    wait_time = between(1, 3)  # 1-3s entre requests

    def on_start(self):
        # Login
        self.client.post('/login/', {
            'username': 'coordenador',
            'password': 'senha123'
        })

    @task(1)
    def criar_solicitacao(self):
        self.client.post('/solicitar/', {
            'data': '15/10/2025',
            'hora_inicio': '09:00',
            'hora_fim': '11:00',
            'formadores': [1],
            'municipio': 1,
            'projeto': 1,
        })

    @task(2)
    def listar_solicitacoes(self):
        self.client.get('/solicitacoes/')
```

**Comando**:
```bash
locust -f locustfile.py --host=http://localhost:8000 --users=50 --spawn-rate=5
```

**SLA**:
- Latência p95: < 500ms
- Taxa de erro: < 1%

---

## 🔄 Continuous Integration (CI)

### GitHub Actions Workflow

```yaml
# .github/workflows/tests.yml
name: Tests
on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    services:
      postgres:
        image: postgres:15
        env:
          POSTGRES_PASSWORD: postgres
        options: >-
          --health-cmd pg_isready
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5

      redis:
        image: redis:7
        options: >-
          --health-cmd "redis-cli ping"
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5

    steps:
      - uses: actions/checkout@v3

      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.13'

      - name: Install dependencies
        run: |
          pip install -r requirements.txt
          pip install pytest pytest-cov pytest-django

      - name: Run unit tests
        run: |
          pytest tests/unit/ --cov=core --cov-report=xml

      - name: Run integration tests
        run: |
          pytest tests/integration/ --cov-append --cov-report=xml

      - name: Upload coverage
        uses: codecov/codecov-action@v3
        with:
          file: ./coverage.xml
          fail_ci_if_error: true

      - name: Run security checks
        run: |
          bandit -r backend/ -ll
          python manage.py check --deploy

  e2e:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3

      - name: Install Playwright
        run: |
          pip install playwright
          playwright install chromium

      - name: Start Django server
        run: |
          docker compose up -d
          sleep 10  # Aguardar containers

      - name: Run E2E tests
        run: |
          pytest tests/e2e/

      - name: Upload test videos
        if: failure()
        uses: actions/upload-artifact@v3
        with:
          name: playwright-videos
          path: tests/e2e/videos/
```

---

## 📋 Test Coverage Report

### Comando

```bash
docker compose exec -T web pytest --cov=core --cov=dat_ingest --cov-report=html
```

### Meta de Cobertura

| Módulo | Cobertura Mínima | Cobertura Atual |
|--------|------------------|-----------------|
| `core/models/` | 95% | _TBD_ |
| `core/services/` | 100% | _TBD_ |
| `core/views/` | 85% | _TBD_ |
| `core/forms/` | 90% | _TBD_ |
| `dat_ingest/` | 80% | _TBD_ |
| **TOTAL** | **90%** | **_TBD_** |

---

## 🎯 Definition of Done (DoD)

**Uma feature só está "Done" quando**:

- [ ] **Code**: Implementação completa conforme spec
- [ ] **Unit Tests**: 100% dos métodos públicos testados
- [ ] **Integration Tests**: Fluxo completo testado (se aplicável)
- [ ] **E2E Tests**: Cenário crítico testado (se aplicável)
- [ ] **Coverage**: Módulo atinge meta de cobertura
- [ ] **Security**: Bandit + Django check passam
- [ ] **Code Review**: Aprovado por pelo menos 1 reviewer
- [ ] **Documentation**: Docstrings + README atualizado
- [ ] **CI**: Todos os testes passando no GitHub Actions

---

**Próximos Passos**: Começar TDD na Fase 3 (Backend Services) conforme `MIGRATION_PLAN.md`.
