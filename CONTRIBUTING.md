# 🤝 Contributing to Sistema Aprender

Obrigado por seu interesse em contribuir com o Sistema Aprender! Este documento fornece diretrizes para garantir um processo de contribuição suave e eficiente.

## 📋 Índice

- [Como Contribuir](#-como-contribuir)
- [Configuração do Ambiente](#-configuração-do-ambiente)
- [Workflow Git](#-workflow-git)
- [Padrões de Code](#-padrões-de-code)
- [Testes](#-testes)
- [Pull Requests](#-pull-requests)
- [Issues](#-issues)
- [Review Process](#-review-process)

## 🚀 Como Contribuir

### Tipos de Contribuições Aceitas

- 🐛 **Bug fixes**: Correção de problemas identificados
- ✨ **Features**: Novas funcionalidades (discussão prévia obrigatória)
- 📚 **Documentação**: Melhorias na documentação
- 🔧 **Refactoring**: Melhorias de código sem mudanças funcionais
- 🧪 **Testes**: Adição ou melhoria de testes
- 🔒 **Security**: Correções de segurança (reporte privado primeiro)

### Antes de Contribuir

1. 🔍 **Verifique issues existentes** - Sua ideia pode já estar sendo trabalhada
2. 💬 **Abra uma issue** para features grandes - Discuta antes de implementar
3. 📖 **Leia a documentação** - Entenda a arquitetura e padrões do projeto

## ⚙️ Configuração do Ambiente

### Requisitos

- Python 3.13+
- PostgreSQL 15+ (ou Docker)
- Git 2.30+
- Node.js 18+ (opcional)

### Setup Local

```bash
# 1. Fork e clone o repositório
git clone https://github.com/SEU_USUARIO/aprender_sistema.git
cd aprender_sistema

# 2. Configure upstream
git remote add upstream https://github.com/REPO_ORIGINAL/aprender_sistema.git

# 3. Crie ambiente virtual
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 4. Instale dependências de desenvolvimento
pip install -r requirements-dev.txt

# 5. Configure pre-commit hooks
pre-commit install

# 6. Configure ambiente
cp .env.example .env
# Edite .env com suas configurações

# 7. Execute setup inicial
make setup  # ou: python manage.py migrate && python manage.py loaddata fixtures/initial_data.json

# 8. Execute testes para verificar
make test
```

### Verificação da Instalação

```bash
# Testes devem passar
python manage.py test

# Linting deve passar
make lint

# Servidor deve iniciar sem erros
make dev
```

## 🌊 Workflow Git

### Estrutura de Branches

```
main (produção)
├── homolog (staging)
│   ├── dev (desenvolvimento)
│   │   ├── feat/nome-da-feature
│   │   ├── fix/nome-do-bug
│   │   └── chore/tarefa-tecnica
```

### Convenção de Branches

| Tipo | Formato | Exemplo |
|------|---------|---------|
| **Feature** | `feat/descricao-breve` | `feat/sistema-notificacoes` |
| **Bug Fix** | `fix/descricao-do-bug` | `fix/validacao-datas` |
| **Chore** | `chore/tarefa-tecnica` | `chore/atualizacao-deps` |
| **Hotfix** | `hotfix/correcao-critica` | `hotfix/vulnerabilidade-csrf` |
| **Docs** | `docs/area-documentacao` | `docs/guia-contribuicao` |

### Fluxo de Trabalho

1. **Sincronize com upstream**:
   ```bash
   git checkout dev
   git pull upstream dev
   ```

2. **Crie branch para sua contribuição**:
   ```bash
   git checkout -b feat/minha-nova-feature
   ```

3. **Faça commits pequenos e descritivos**:
   ```bash
   git add .
   git commit -m "feat: adicionar validação de CPF no formulário"
   ```

4. **Mantenha sua branch atualizada**:
   ```bash
   git pull upstream dev --rebase
   ```

5. **Push e abra Pull Request**:
   ```bash
   git push origin feat/minha-nova-feature
   ```

## 📝 Padrões de Code

### Convenção de Commits (Conventional Commits)

```bash
<tipo>(<escopo>): <descrição>

[corpo opcional]

[footer(s) opcional(is)]
```

**Tipos permitidos**:
- `feat`: Nova funcionalidade
- `fix`: Correção de bug
- `docs`: Documentação
- `style`: Formatação (não afeta lógica)
- `refactor`: Refatoração de código
- `test`: Adição/modificação de testes
- `chore`: Tarefas de manutenção

**Exemplos**:
```bash
feat(core): adicionar sistema de notificações por email
fix(auth): corrigir validação de CPF em formulários
docs(readme): atualizar instruções de instalação
test(models): adicionar testes para modelo Usuario
chore(deps): atualizar Django para 5.2.4
```

### Python Code Style

Seguimos **PEP 8** com configurações específicas:

```python
# pyproject.toml (já configurado)
[tool.black]
line-length = 88
target-version = ['py313']

[tool.isort]
profile = "black"
line_length = 88
multi_line_output = 3

[tool.flake8]
max-line-length = 88
exclude = [".git", "__pycache__", "venv", "migrations"]
```

### Django Patterns

#### Models
```python
from django.db import models
from django.utils.translation import gettext_lazy as _

class MinhaModel(models.Model):
    """Docstring explicando o modelo."""
    
    nome = models.CharField(
        _("Nome"), 
        max_length=255,
        help_text=_("Nome completo do usuário")
    )
    
    class Meta:
        verbose_name = _("Minha Model")
        verbose_name_plural = _("Minhas Models")
        
    def __str__(self):
        return self.nome
```

#### Views
```python
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import ListView

class MinhaView(LoginRequiredMixin, ListView):
    """Docstring explicando a view."""
    
    model = MinhaModel
    template_name = "app/template.html"
    context_object_name = "objetos"
    paginate_by = 20
```

#### Services
```python
# core/services/meu_service.py
from typing import Optional
from django.db import transaction

class MeuService:
    """Service para lógica de negócio complexa."""
    
    @staticmethod
    @transaction.atomic
    def criar_objeto(dados: dict) -> Optional[MinhaModel]:
        """Cria objeto com validações específicas."""
        # Lógica aqui
        return objeto
```

## 🧪 Testes

### Estrutura de Testes

```
tests/
├── unit/           # Testes unitários
│   ├── test_models.py
│   ├── test_views.py
│   └── test_services.py
├── integration/    # Testes de integração
│   ├── test_google_calendar.py
│   └── test_workflows.py
└── e2e/           # Testes end-to-end
    ├── test_user_flows.py
    └── conftest.py
```

### Executando Testes

```bash
# Todos os testes
make test

# Testes específicos
python manage.py test core.tests.test_models

# Com coverage
make test-coverage

# Testes E2E (Playwright)
pytest tests/e2e/ -v
```

### Escrevendo Testes

```python
from django.test import TestCase
from django.contrib.auth import get_user_model

class TesteModelo(TestCase):
    """Testes para o modelo Usuario."""
    
    def setUp(self):
        """Configuração executada antes de cada teste."""
        self.user_model = get_user_model()
    
    def test_criar_usuario_valido(self):
        """Deve criar usuário com dados válidos."""
        user = self.user_model.objects.create_user(
            username="teste@email.com",
            password="senha123"
        )
        
        self.assertTrue(user.is_active)
        self.assertEqual(user.username, "teste@email.com")
```

### Coverage Requirements

- **Minimum coverage**: 80%
- **New code coverage**: 90%
- **Critical paths**: 100% (auth, payments, etc.)

## 📝 Pull Requests

### Antes de Abrir o PR

- [ ] ✅ Testes passando (`make test`)
- [ ] ✅ Linting aprovado (`make lint`)
- [ ] ✅ Cobertura adequada (>80%)
- [ ] ✅ Documentação atualizada
- [ ] ✅ Commits organizados
- [ ] ✅ Branch atualizada com dev

### Template do PR

Use o template automático `.github/PULL_REQUEST_TEMPLATE.md` que inclui:

1. **Descrição** clara da mudança
2. **Tipo de mudança** (feature/bugfix/docs)
3. **Testes** realizados
4. **Checklist** de verificação
5. **Screenshots** (se aplicável)

### Process de Review

1. **Automated checks** devem passar
2. **Code review** por pelo menos 1 maintainer
3. **Functional testing** se necessário
4. **Documentation review** se aplicável

## 🐛 Issues

### Reportando Bugs

Use o template `.github/ISSUE_TEMPLATE/bug_report.md`:

- **Descrição** clara do problema
- **Steps to reproduce**
- **Comportamento esperado vs atual**
- **Ambiente** (OS, Python, Django versions)
- **Screenshots/logs** se aplicável

### Solicitando Features

Use `.github/ISSUE_TEMPLATE/feature_request.md`:

- **Problema** que a feature resolve
- **Solução proposta**
- **Alternativas consideradas**
- **Contexto adicional**

### Priorização de Issues

| Label | Prioridade | SLA |
|-------|------------|-----|
| `critical` | P0 | 24h |
| `high` | P1 | 1 semana |
| `medium` | P2 | 2 semanas |
| `low` | P3 | Best effort |

## 👀 Review Process

### Para Reviewers

#### Checklist de Review

- [ ] **Funcionalidade**: O código faz o que deveria?
- [ ] **Testes**: Cobertura adequada e testes relevantes?
- [ ] **Performance**: Não introduz problemas de performance?
- [ ] **Segurança**: Não introduz vulnerabilidades?
- [ ] **Padrões**: Segue padrões do projeto?
- [ ] **Documentação**: Documentação atualizada?

#### Tipos de Review

- 🟢 **LGTM** - Looks good to me (aprovado)
- 🟡 **Request Changes** - Necessita mudanças
- 🔴 **Block** - Bloqueia merge (problemas sérios)

### Para Contributors

#### Respondendo a Reviews

- ✅ **Seja receptivo** ao feedback
- 🔄 **Faça as mudanças** solicitadas
- 💬 **Responda** aos comentários
- ✔️ **Marque como resolvido** após corrigir

#### Quando Discordar

1. **Explique seu ponto** com argumentos técnicos
2. **Proponha alternativas** se aplicável
3. **Aceite a decisão** do maintainer

## 🏷️ Release Process

### Semantic Versioning

- `MAJOR.MINOR.PATCH` (ex: 1.2.3)
- **MAJOR**: Breaking changes
- **MINOR**: New features (backward compatible)
- **PATCH**: Bug fixes

### Branch Strategy

- `main`: Produção (estável)
- `homolog`: Staging (testes finais)
- `dev`: Desenvolvimento (integration)

## 📞 Obtendo Ajuda

### Canais de Comunicação

- 💬 **GitHub Issues**: Bugs e features
- 📧 **Email**: dev@aprender.com
- 📚 **Wiki**: Documentação técnica detalhada

### Mentoria

Novos contributors podem solicitar mentoria:
- Marque a issue com `good-first-issue`
- Comente na issue mencionando `@maintainers`

## 🎯 Code of Conduct

Esperamos que todos os contributors sigam nosso código de conduta:

- 🤝 **Seja respeitoso** com outros contributors
- 🎯 **Foque no problema**, não na pessoa
- 🌟 **Celebre** as contribuições dos outros
- 📚 **Compartilhe conhecimento**
- 🛡️ **Reporte comportamentos inadequados**

## 📋 Checklist Final

Antes de enviar sua contribuição:

- [ ] Li e entendi este guia
- [ ] Configurei o ambiente corretamente
- [ ] Testes estão passando
- [ ] Código segue os padrões estabelecidos
- [ ] Documentação foi atualizada
- [ ] Commit messages seguem convenções
- [ ] PR está bem descrito

---

**🎉 Obrigado por contribuir com o Sistema Aprender!**

Sua participação ajuda a transformar a educação através da tecnologia. 

*Para dúvidas sobre este guia, abra uma issue com a label `documentation`.*