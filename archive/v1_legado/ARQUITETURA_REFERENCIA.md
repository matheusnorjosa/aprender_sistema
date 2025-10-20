# Arquitetura de Referência - Sistema Aprender

## Visão Geral

O Sistema Aprender é uma plataforma web desenvolvida em Django para substituir o processo manual de planilhas Google/Excel no controle de eventos educacionais. O sistema automatiza o fluxo de solicitações, verificação de conflitos, aprovações e criação de eventos no Google Calendar.

## Arquitetura Técnica

### Stack Tecnológico
- **Backend**: Python 3.13 + Django 5.2.4
- **Banco de Dados**: PostgreSQL 15
- **Infraestrutura**: Docker + Docker Compose
- **Frontend**: HTML5 + Bootstrap 5.3 + JavaScript ES6+
- **Integração**: Google Calendar API + Google Meet
- **Cache**: Redis (produção) / LocMem (desenvolvimento)
- **Timezone**: America/Fortaleza (UTC-3)

### Arquitetura de Camadas

```
┌─────────────────────────────────────────────────────────────┐
│                    CAMADA DE APRESENTAÇÃO                    │
├─────────────────────────────────────────────────────────────┤
│ Templates Django + Bootstrap + JavaScript                    │
│ • home.html (dashboard principal)                           │
│ • mapa_mensal_view.html (visualização de disponibilidade)   │
│ • solicitacao_form.html (formulário de eventos)            │
│ • aprovacoes_pendentes.html (fluxo de aprovações)          │
└─────────────────────────────────────────────────────────────┘
                                │
┌─────────────────────────────────────────────────────────────┐
│                    CAMADA DE CONTROLE                        │
├─────────────────────────────────────────────────────────────┤
│ Views Django (urls.py + views/)                             │
│ • base.py - Views base e dashboard                          │
│ • gestao_views.py - Gestão de recursos                     │
│ • mapa_views.py - Visualização de disponibilidade          │
│ • diretoria_views.py - Aprovações e controle               │
└─────────────────────────────────────────────────────────────┘
                                │
┌─────────────────────────────────────────────────────────────┐
│                   CAMADA DE SERVIÇOS                         │
├─────────────────────────────────────────────────────────────┤
│ Services (core/services/)                                   │
│ • data_services.py - Processamento de dados                │
│ • notification_service.py - Notificações                   │
│ • calendar_codes.py - Integração Google Calendar           │
│ • Verificação de conflitos e disponibilidade               │
└─────────────────────────────────────────────────────────────┘
                                │
┌─────────────────────────────────────────────────────────────┐
│                    CAMADA DE DADOS                           │
├─────────────────────────────────────────────────────────────┤
│ Models Django (core/models.py)                              │
│ • Usuario, Formador, Projeto, Municipio                    │
│ • Solicitacao, Aprovacao, TipoEvento                       │
│ • DisponibilidadeFormador, LogAuditoria                    │
└─────────────────────────────────────────────────────────────┘
                                │
┌─────────────────────────────────────────────────────────────┐
│                CAMADA DE PERSISTÊNCIA                        │
├─────────────────────────────────────────────────────────────┤
│ PostgreSQL 15 (Docker Container)                            │
│ • Porta 5433 (desenvolvimento)                             │
│ • Backup automático e migração de dados                    │
└─────────────────────────────────────────────────────────────┘
```

## Modelos de Dados

### Entidades Principais

#### Usuario
```python
class Usuario(AbstractUser):
    cpf = models.CharField(max_length=14, unique=True)
    papel = models.CharField(choices=PAPEL_CHOICES)
    municipio = models.ForeignKey(Municipio)
    telefone = models.CharField(max_length=20)
    observacoes = models.TextField()
```

#### Formador
```python
class Formador(models.Model):
    usuario = models.OneToOneField(Usuario)
    areas_atuacao = models.ManyToManyField(TipoEvento)
    disponibilidade_padrao = models.JSONField()
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
    status = models.CharField(choices=STATUS_CHOICES)
```

### Relacionamentos

```
Usuario 1:1 Formador
Usuario N:1 Municipio
Solicitacao N:M Formador
Solicitacao N:1 Projeto
Solicitacao N:1 TipoEvento
Solicitacao N:1 Municipio
Aprovacao 1:1 Solicitacao
LogAuditoria N:1 Usuario
```

## Fluxos de Processo

### 1. Fluxo de Solicitação de Evento

```
┌─────────────┐    ┌─────────────┐    ┌─────────────┐    ┌─────────────┐
│  Solicitação│───▶│ Verificação │───▶│  Aprovação  │───▶│   Google    │
│   de Evento │    │ Conflitos   │    │   Manual    │    │  Calendar   │
└─────────────┘    └─────────────┘    └─────────────┘    └─────────────┘
       │                   │                   │                   │
       ▼                   ▼                   ▼                   ▼
┌─────────────┐    ┌─────────────┐    ┌─────────────┐    ┌─────────────┐
│ Coordenador │    │   Sistema   │    │Superintend. │    │ Evento +    │
│ preenche    │    │ verifica    │    │ analisa e   │    │ Google Meet │
│ formulário  │    │ disponib.   │    │ decide      │    │ Link        │
└─────────────┘    └─────────────┘    └─────────────┘    └─────────────┘
```

### 2. Verificação de Conflitos

O sistema implementa as seguintes verificações automáticas:

#### RD-01: Não-sobreposição
- Verifica se formador já tem evento no mesmo período
- Algoritmo: `if not (fim_A <= inicio_B or fim_B <= inicio_A): conflito()`

#### RD-02: Bloqueio Total (T)
- Impede qualquer evento no período bloqueado
- Status: `BLOQUEIO_TOTAL`

#### RD-03: Bloqueio Parcial (P)
- Permite eventos fora do subintervalo bloqueado
- Status: `BLOQUEIO_PARCIAL`

#### RD-04: Buffer de Deslocamento (D)
- Entre municípios diferentes: mínimo 60-120 minutos
- Mesmo município: buffer zero

#### RD-05: Capacidade Diária (M)
- Limite configur ável de horas por dia
- Status: `MULTIPLOS_EVENTOS`

## Integrações Externas

### Google Calendar API

```python
# core/services/calendar_codes.py
class GoogleCalendarService:
    def criar_evento(self, solicitacao):
        """Cria evento no Google Calendar após aprovação"""

    def gerar_meet_link(self, evento_id):
        """Gera link do Google Meet automaticamente"""

    def verificar_conflitos_externos(self, formador, data_inicio, data_fim):
        """Verifica conflitos no calendário externo"""
```

### Fluxo de Autenticação OAuth2
1. Configuração de credenciais no Google Cloud Console
2. Autorização inicial via script `configurar_oauth.py`
3. Renovação automática de tokens
4. Fallback para criação manual em caso de falha

## Segurança e Auditoria

### Controle de Acesso
- **Django Groups & Permissions**: controle granular de funcionalidades
- **Perfis definidos**: Superintendência, Coordenador, Formador, Admin
- **Views protegidas**: `@login_required` + verificação de papel

### Auditoria Completa
```python
class LogAuditoria(models.Model):
    usuario = models.ForeignKey(Usuario)
    acao = models.CharField(max_length=100)
    modelo_afetado = models.CharField(max_length=50)
    objeto_id = models.PositiveIntegerField()
    dados_anteriores = models.JSONField()
    dados_novos = models.JSONField()
    timestamp = models.DateTimeField(auto_now_add=True)
    ip_origem = models.GenericIPAddressField()
```

### Proteção de Dados Sensíveis
- **Senhas**: Hash bcrypt via Django
- **Tokens OAuth**: Criptografados em variáveis de ambiente
- **Logs**: Sem exposição de dados pessoais
- **Backup**: Automatizado com criptografia

## Performance e Escalabilidade

### Otimizações de Database
```python
# Consultas otimizadas
formadores = Formador.objects.select_related('usuario', 'municipio')
                            .prefetch_related('areas_atuacao')

# Índices estratégicos
class Meta:
    indexes = [
        models.Index(fields=['data_inicio', 'data_fim']),
        models.Index(fields=['status', 'municipio']),
    ]
```

### Caching Strategy
- **Redis**: Cache de disponibilidade e consultas frequentes
- **Template Cache**: Fragmentos dinâmicos
- **Database Connection Pool**: Conexões reutilizadas

### Estratégia de Deploy

#### Desenvolvimento
```bash
# Docker Compose local
docker-compose up -d
ENVIRONMENT=staging python manage.py runserver
```

#### Produção
```bash
# Render.com (recomendado)
ENVIRONMENT=production
ALLOWED_HOSTS=sistema.render.com
DATABASE_URL=postgresql://...
SECRET_KEY=...
```

## Monitoramento e Observabilidade

### Logs Estruturados
```python
import structlog
logger = structlog.get_logger(__name__)

# Exemplo de uso
logger.info(
    "solicitacao_criada",
    solicitacao_id=solicitacao.id,
    usuario=request.user.username,
    formadores=[f.nome for f in formadores]
)
```

### Métricas de Negócio
- Taxa de aprovação de solicitações
- Tempo médio de processamento
- Conflitos por formador/mês
- Utilização de calendário por região

## Testes e Qualidade

### Estratégia de Testes
```
┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐
│  Testes Unit.   │  │  Testes Integr. │  │  Testes E2E     │
│                 │  │                 │  │                 │
│ • Models        │  │ • APIs          │  │ • Fluxos        │
│ • Services      │  │ • Views         │  │ • Navegação     │
│ • Utils         │  │ • Forms         │  │ • Integrações   │
└─────────────────┘  └─────────────────┘  └─────────────────┘
      95%+                  90%+                  85%+
```

### Cobertura Obrigatória
- **Verificação de conflitos**: 100%
- **Fluxo de aprovações**: 100%
- **Integrações críticas**: 95%+
- **Models e validações**: 95%+

## Documentação Técnica

### Estrutura da Documentação
```
docs/
├── technical/
│   ├── ARQUITETURA_REFERENCIA.md (este arquivo)
│   ├── API_DOCUMENTATION.md
│   └── DATABASE_SCHEMA.md
├── user/
│   ├── MANUAL_USUARIO.md
│   └── GUIA_COORDENADOR.md
└── api/
    └── endpoints_spec.yaml
```

### Padrões de Código
- **PEP 8**: Formatação de código Python
- **Type Hints**: Obrigatório em funções públicas
- **Docstrings**: Google Style para documentação
- **Commits**: Conventional Commits

## Roadmap Técnico

### Fase 1 (Atual) - MVP ✅
- Sistema básico de solicitações
- Verificação de conflitos
- Fluxo de aprovação manual
- Integração Google Calendar

### Fase 2 - Melhorias
- Dashboard analítico avançado
- Notificações em tempo real
- API REST completa
- Mobile-responsive otimizado

### Fase 3 - Escalabilidade
- Microserviços (separar integrações)
- Event Sourcing para auditoria
- Machine Learning para predições
- Multi-tenancy

## Considerações Finais

Esta arquitetura foi desenhada para:
- **Manutenibilidade**: Código limpo e bem estruturado
- **Escalabilidade**: Suporte a crescimento de usuários e dados
- **Confiabilidade**: Processos críticos com redundância
- **Segurança**: Proteção de dados e auditoria completa
- **Usabilidade**: Interface intuitiva seguindo ISO 9241-110

A evolução da arquitetura deve sempre considerar esses pilares fundamentais.