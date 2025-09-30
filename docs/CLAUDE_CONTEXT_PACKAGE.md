# Claude Context Package - Sistema Aprender

## Introdução

Este documento contém o contexto completo e estruturado do Sistema Aprender para facilitar o trabalho de assistentes de IA (Claude, ChatGPT, etc.). Ele consolida todas as informações essenciais em um formato otimizado para upload e referência rápida.

## Resumo Executivo

### Projeto
- **Nome**: Sistema Aprender (AS)
- **Objetivo**: Substituir planilhas Google/Excel por sistema web automatizado para gestão de eventos educacionais
- **Status**: MVP implementado, em fase de consolidação e melhorias
- **Stack**: Python 3.13 + Django 5.2 + PostgreSQL 15 + Docker

### Situação Atual (Setembro 2025)
- ✅ **Sistema operacional** com dados reais importados (1.915 solicitações)
- ✅ **88 formadores** ativos cadastrados
- ✅ **74 municípios** configurados
- ✅ **24 projetos** educacionais
- ✅ **Ambiente Docker unificado** funcionando
- ✅ **APIs REST** para mapa de disponibilidade
- ✅ **Fluxo de aprovação manual** implementado

## Arquitetura do Sistema

### Estrutura de Diretórios
```
aprender_sistema/
├── core/                          # App principal Django
│   ├── models.py                  # Modelos de dados principais
│   ├── views/                     # Views organizadas por funcionalidade
│   ├── templates/core/            # Templates HTML
│   ├── services/                  # Serviços de negócio
│   ├── management/commands/       # Comandos Django personalizados
│   └── migrations/                # Migrações do banco
├── aprender_sistema/              # Configurações Django
│   ├── settings.py               # Configurações unificadas
│   └── urls.py                   # URLs principais
├── static/                       # Arquivos estáticos
├── templates/                    # Templates globais
├── docs/                         # Documentação
├── scripts/                      # Scripts auxiliares
├── docker-compose.yml            # Configuração Docker
└── requirements.txt              # Dependências Python
```

### Modelos de Dados Principais

#### Usuario (estende AbstractUser)
```python
class Usuario(AbstractUser):
    cpf = models.CharField(max_length=14, unique=True)
    papel = models.CharField(choices=PAPEL_CHOICES)  # COORDENADOR, SUPERINTENDENCIA, FORMADOR
    municipio = models.ForeignKey(Municipio)
    telefone = models.CharField(max_length=20)
    observacoes = models.TextField(blank=True)
```

#### Formador
```python
class Formador(models.Model):
    usuario = models.OneToOneField(Usuario)
    areas_atuacao = models.ManyToManyField(TipoEvento)
    disponibilidade_padrao = models.JSONField(default=dict)
    ativo = models.BooleanField(default=True)
```

#### Solicitacao
```python
class Solicitacao(models.Model):
    solicitante = models.ForeignKey(Usuario)
    formadores = models.ManyToManyField(Formador)
    projeto = models.ForeignKey(Projeto)
    tipo_evento = models.ForeignKey(TipoEvento)
    municipio = models.ForeignKey(Municipio)
    data_inicio = models.DateTimeField()
    data_fim = models.DateTimeField()
    status = models.CharField(choices=STATUS_CHOICES)  # PENDENTE, APROVADO, REJEITADO
    observacoes = models.TextField(blank=True)
```

## Funcionalidades Implementadas

### 1. Gestão de Usuários e Permissões
- Sistema baseado em **Django Groups & Permissions**
- **3 papéis principais**: Coordenador, Superintendência, Formador
- **Controle granular** de acesso por funcionalidade
- **Auditoria completa** de ações via LogAuditoria

### 2. Solicitação de Eventos
- **Formulário web** para criar solicitações
- **Validação automática** de datas e conflitos
- **Seleção de formadores** por município
- **Upload de documentos** (se necessário)

### 3. Verificação de Conflitos
Implementa 5 regras de negócio (RD-01 a RD-05):
- **RD-01**: Não-sobreposição de eventos
- **RD-02**: Bloqueio total (T)
- **RD-03**: Bloqueio parcial (P)
- **RD-04**: Buffer de deslocamento entre municípios
- **RD-05**: Capacidade diária máxima

### 4. Fluxo de Aprovação
- **Aprovação manual obrigatória** pela Superintendência
- **Interface dedicada** para aprovações pendentes
- **Histórico completo** de decisões
- **Notificações** automáticas

### 5. Mapa de Disponibilidade
- **API JSON** `/mapa-mensal/?ano=YYYY&mes=MM`
- **Visualização gráfica** similar às planilhas originais
- **Códigos visuais**: E, M, D, P, T, X para diferentes status
- **Filtros** por formador, município, projeto

### 6. Integração Google Calendar
- **OAuth2** configurado para acesso
- **Criação automática** de eventos após aprovação
- **Links Google Meet** gerados automaticamente
- **Sincronização bidirecional** (planejada)

## Dados Atuais do Sistema

### Estatísticas de Produção
- **1.915 solicitações** importadas (período: 2025-01-29 a 2025-12-05)
- **88 formadores** ativos
- **74 municípios** cadastrados
- **24 projetos** configurados
- **20 tipos de evento** disponíveis

### Principais Projetos (por volume)
1. **ACerta**: 426 eventos (22%)
2. **Novo Lendo**: 399 eventos (21%)
3. **Tema**: 287 eventos (15%)
4. **Lendo e Escrevendo**: 179 eventos (9%)
5. **Brincando e Aprendendo**: 150 eventos (8%)

### Coordenadores Principais
- Ellen Damares (coordenadora principal)
- Aurea Lucia (coordenadora adjunta)
- Maria Nadir (gerente de projetos)
- Rafael Rabelo (supervisor técnico)

## Comandos Importantes

### Desenvolvimento Local
```bash
# Iniciar ambiente Docker
docker-compose up -d

# Rodar servidor Django
ENVIRONMENT=staging DB_HOST=localhost DB_PORT=5433 \
DB_NAME=aprender_sistema_db DB_USER=adm_aprender \
DB_PASSWORD=aprender123456 python manage.py runserver

# Aplicar migrações
python manage.py migrate

# Criar superusuário
python manage.py createsuperuser

# Executar testes
python manage.py test
```

### Comandos Específicos do Sistema
```bash
# Importar dados da planilha principal
python manage.py import_agenda_completa --verbose

# Importar aba específica
python manage.py import_agenda_completa --aba Super --verbose

# Simulação (dry-run)
python manage.py import_agenda_completa --dry-run --verbose

# Validar dados importados
python manage.py validate_unified_data

# Sincronizar papéis de usuário
python manage.py sincronizar_papeis_planilha
```

## Configurações de Ambiente

### Variáveis Obrigatórias
```bash
# Ambiente
ENVIRONMENT=development|staging|production

# Database
DB_HOST=localhost
DB_PORT=5433
DB_NAME=aprender_sistema_db
DB_USER=adm_aprender
DB_PASSWORD=aprender123456

# Security
SECRET_KEY=sua_chave_secreta
ALLOWED_HOSTS=localhost,127.0.0.1

# Google Calendar (opcional)
GOOGLE_OAUTH2_CLIENT_ID=seu_client_id
GOOGLE_OAUTH2_CLIENT_SECRET=seu_client_secret
```

### URLs Principais
- **Home**: `/` - Dashboard principal
- **Solicitações**: `/solicitar/` - Criar nova solicitação
- **Aprovações**: `/aprovacoes/pendentes/` - Pendentes de aprovação
- **Mapa**: `/disponibilidade/` - Mapa mensal de disponibilidade
- **Bloqueios**: `/bloqueios/novo/` - Bloquear agenda de formador
- **Admin**: `/admin/` - Interface administrativa Django

## Padrões de Código

### Python/Django
- **PEP 8** obrigatório (formatação com Black)
- **Type hints** em todas as funções públicas
- **Docstrings** no estilo Google
- **Validação robusta** de entrada
- **Logs estruturados** para auditoria

### Templates
- **Bootstrap 5.3** para responsividade
- **CSRF tokens** obrigatórios em forms
- **Escape automático** do Django (segurança XSS)
- **Hierarquia clara** base.html → seção → página

### Banco de Dados
- **PostgreSQL** com constraints apropriados
- **Índices** em campos de busca frequente
- **Migrations** versionadas
- **Backup automático** configurado

## Integrações Externas

### Google Calendar API
```python
# Configuração OAuth2
GOOGLE_OAUTH2_SCOPES = [
    'https://www.googleapis.com/auth/calendar',
    'https://www.googleapis.com/auth/calendar.events'
]

# Calendar ID institucional
CALENDAR_ID = 'c_3381579109915e33c06be465adfbd9a31aaf4205c0bd45aa050c5a18be99fe15@group.calendar.google.com'
```

### Status da Integração
- ✅ **Credenciais OAuth2** configuradas
- ✅ **Scripts de autenticação** funcionais
- ⚠️ **Escopo calendar** precisa ser reautorizado
- ✅ **Fallback manual** implementado

## Regras de Negócio

### Fluxo de Aprovação (Obrigatório)
1. **Coordenador** cria solicitação
2. **Sistema** verifica conflitos automaticamente
3. **Superintendência** aprova/rejeita manualmente
4. **Sistema** cria evento no Google Calendar (se aprovado)
5. **Auditoria** registra todas as ações

### Verificação de Conflitos
O sistema implementa verificação automática baseada em 5 regras:
- **Sobreposição**: Mesmo formador, mesmo período
- **Bloqueios**: Totais (T) ou parciais (P)
- **Deslocamento**: Buffer entre municípios diferentes
- **Capacidade**: Limite de horas por dia
- **Status**: Eventos já aprovados têm prioridade

### Códigos de Status Visual
- **E**: Evento confirmado
- **M**: Múltiplos eventos (capacidade)
- **D**: Deslocamento necessário
- **P**: Bloqueio parcial
- **T**: Bloqueio total
- **X**: Conflito geral

## Problemas Conhecidos e Soluções

### 1. OAuth2 Google Calendar
**Problema**: Escopo 'calendar' não autorizado
**Solução**: Executar `python scripts/renew_google_calendar_auth.py`

### 2. MCPs no Docker
**Problema**: MCP registration failures
**Solução**: MCPs desabilitados temporariamente (settings.py linha 156)

### 3. Cache do Browser
**Problema**: Menu não atualiza após mudanças
**Solução**: Ctrl+Shift+R para limpar cache

### 4. Performance de Queries
**Problema**: Consultas N+1 em relatórios
**Solução**: Usar select_related() e prefetch_related()

## Segurança

### Implementado
- ✅ **CSRF Protection** em todos os forms
- ✅ **SQL Injection** prevenido via ORM Django
- ✅ **XSS Protection** via auto-escape templates
- ✅ **Auditoria completa** de ações sensíveis
- ✅ **Controle de acesso** baseado em papéis
- ✅ **HTTPS** obrigatório em produção

### Configurações de Segurança
```python
# settings.py - Produção
SECURE_SSL_REDIRECT = True
SECURE_HSTS_SECONDS = 31536000
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
X_FRAME_OPTIONS = 'DENY'
```

## Testes

### Cobertura Atual
- **Models**: 95%+ cobertura
- **Views**: 90%+ cobertura
- **Services**: 85%+ cobertura
- **Integration**: Fluxos críticos testados

### Executar Testes
```bash
# Todos os testes
python manage.py test

# Testes específicos
python manage.py test core.tests.test_models
python manage.py test core.tests.test_availability

# Com cobertura
coverage run --source='.' manage.py test
coverage report
coverage html
```

## Deploy e Infraestrutura

### Recomendação: Render.com
- **PostgreSQL gratuito** incluído
- **Deploy automático** via Git
- **HTTPS** configurado automaticamente
- **Logs** centralizados
- **Backup** automático do banco

### Configuração Docker Local
```yaml
# docker-compose.yml
version: '3.8'
services:
  db:
    image: postgres:15
    environment:
      POSTGRES_DB: aprender_sistema_db
      POSTGRES_USER: adm_aprender
      POSTGRES_PASSWORD: aprender123456
    ports:
      - "5433:5432"
```

## Próximos Passos

### Curto Prazo (1-2 meses)
- [ ] **Deploy em produção** (Render.com)
- [ ] **Correção OAuth2** Google Calendar
- [ ] **Testes de carga** com dados reais
- [ ] **Treinamento** da equipe

### Médio Prazo (3-6 meses)
- [ ] **API REST completa** para integrações
- [ ] **Dashboard analítico** avançado
- [ ] **Notificações** em tempo real
- [ ] **Mobile responsivo** otimizado

### Longo Prazo (6-12 meses)
- [ ] **Machine Learning** para predições
- [ ] **Sincronização bidirecional** Google Calendar
- [ ] **Multi-tenancy** para outras instituições
- [ ] **APP móvel** nativo

## Contatos e Suporte

### Equipe Técnica
- **Desenvolvedor Principal**: Claude Code + equipe local
- **Administrador de Sistema**: [Definir]
- **Coordenação Pedagógica**: Ellen Damares, Aurea Lucia

### Documentação Adicional
- **Arquitetura**: `ARQUITETURA_REFERENCIA.md`
- **Padrões de Código**: `PADROES_CODIGO_PYTHON.md`
- **Segurança**: `GUIA_SEGURANCA.md`
- **Manual do Usuário**: `docs/user/MANUAL_USUARIO.md`

## Informações de Contexto para IA

### Ao trabalhar com este sistema:
1. **Sempre verificar** o estado atual via git status
2. **Ler CLAUDE.md** para contexto da sessão atual
3. **Usar TodoWrite** para planejamento de tarefas
4. **Seguir padrões** definidos nos arquivos de documentação
5. **Testar mudanças** antes de commitar
6. **Documentar** decisões importantes

### Comandos úteis para debugging:
```bash
# Ver status atual
git status
docker-compose ps

# Logs do sistema
docker-compose logs web
tail -f logs/aprender.log

# Shell Django
python manage.py shell_plus

# Verificar banco
python manage.py dbshell
```

### Estrutura de branches:
- **main**: Produção estável
- **develop**: Desenvolvimento ativo
- **feature/***: Novas funcionalidades
- **fix/***: Correções de bugs

### Fluxo de trabalho recomendado:
1. Analisar requisito/problema
2. Criar todo list se necessário
3. Implementar solução
4. Testar localmente
5. Executar lint/typecheck
6. Commitar com mensagem descritiva
7. Atualizar documentação se necessário

---

Este documento deve ser atualizado conforme o sistema evolui. Última atualização: Setembro 2025.