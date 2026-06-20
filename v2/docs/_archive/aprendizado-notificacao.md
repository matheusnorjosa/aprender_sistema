# Aprendizado: Sistema de Notificações de Timing

**Data**: 2025-12-19
**Versão**: 1.0
**Status**: Análise Completa - Pronto para Implementação

---

## 1. Contexto do Problema

### 1.1 Necessidade de Negócio

O sistema precisa notificar **formadores**, **coordenadores** e **gerentes** sobre o cumprimento de prazos ideais para aplicação de formações/encontros. Cada projeto/coleção tem:

- Um **tempo ideal** para aplicação das formações
- Um **período ideal** entre os eventos formativos
- Uma **quantidade específica** de encontros

### 1.2 Regra de Negócio Principal

```
Contato Município (Dia 0) → 1º Encontro → 2º Encontro → ... → Nº Encontro
                                    ↓              ↓                  ↓
                               [X dias]       [Y dias]           [Z dias]
```

A contagem de tempo é **cumulativa a partir do Contato com Município** (Dia 0), não entre etapas individuais.

### 1.3 Notificação em Cascata

A notificação escala hierarquicamente:
1. **Formador** (responsável direto) - Primeiro alerta
2. **Coordenador** (se não resolvido) - Escalação após N dias
3. **Gerente** (se persistir) - Escalação final após M dias

---

## 2. Análise do Sistema Existente

### 2.1 Estrutura de Páginas do Sistema

| Rota | Página | Relevância |
|------|--------|------------|
| `/dat-module/acoes` | AcoesPage | ⭐⭐⭐ **CRÍTICO** - Captura Dia 0 |
| `/dat-module/formacoes` | FormacoesPage | ⭐⭐ Captura encontros |
| `/dat-module/coordenadores` | CoordenadoresPage | ⭐ Hierarquia |
| `/dat-module/compras` | ComprasPage | Baixa - Materiais |
| `/dat-module/cadastros` | CadastrosPage | Média - Workflow paralelo |
| `/solicitacoes/nova` | NewSolicitacaoWizard | Solicitações de eventos |
| `/admin-dat/projetos` | ProjetosPage | Config de projetos |

### 2.2 Modelos Existentes Relevantes

#### 2.2.1 DATAcao (Prospecção)
**Arquivo**: `v2/backend/apps/core/models/workflow.py`
**Página**: `/dat-module/acoes`

```python
class DATAcao(models.Model):
    municipio = models.ForeignKey(Municipio)
    projeto = models.ForeignKey(Projeto)
    coordenador = models.ForeignKey(Usuario)
    area = models.CharField(max_length=100)

    # Etapa 1: Carta
    status_carta = models.CharField(choices=STATUS_CHOICES)
    data_carta = models.DateField(null=True)
    observacao_carta = models.TextField(blank=True)

    # Etapa 2: Contato ⭐⭐⭐ DIA 0
    status_contato = models.CharField(choices=STATUS_CHOICES)
    data_contato = models.DateField(null=True)  # ← BASE DOS PRAZOS
    observacao_contato = models.TextField(blank=True)

    # Etapa 3: Reunião
    status_reuniao = models.CharField(choices=STATUS_CHOICES)
    data_reuniao = models.DateField(null=True)
    observacao_reuniao = models.TextField(blank=True)

    # Etapa 4: Entrega
    status_entrega = models.CharField(choices=STATUS_CHOICES)
    data_entrega = models.DateField(null=True)
    observacao_entrega = models.TextField(blank=True)
```

**Status possíveis**: `pendente`, `em_andamento`, `concluido`, `cancelado`

#### 2.2.2 DATFormacao (Encontros)
**Página**: `/dat-module/formacoes`

```python
class DATFormacao(models.Model):
    projeto = models.ForeignKey(Projeto)
    municipio = models.ForeignKey(Municipio)
    coordenador = models.ForeignKey(Usuario)
    formador_nome = models.CharField(max_length=200)

    data_formacao = models.DateField()  # Data do encontro
    horario_inicio = models.TimeField()
    horario_fim = models.TimeField()

    modalidade = models.CharField()  # presencial/online/hibrida
    status = models.CharField()  # agendada/confirmada/realizada/cancelada

    quantidade_prevista = models.IntegerField()
    quantidade_presente = models.IntegerField()

    # Documentação
    lista_presenca_enviada = models.BooleanField()
    relatorio_enviado = models.BooleanField()
    fotos_enviadas = models.BooleanField()
```

**LACUNA**: Não tem campo `numero_encontro` (1º, 2º, 3º...)

#### 2.2.3 DATCoordenador
**Página**: `/dat-module/coordenadores`

```python
class DATCoordenador(models.Model):
    nome = models.CharField(max_length=200)
    area = models.CharField(max_length=100)  # DAT, Pedagógico, etc.
    cargo = models.CharField(max_length=100)
    email = models.EmailField()
    telefone = models.CharField()
    ativo = models.BooleanField()

    # Métricas
    total_municipios = models.IntegerField()
    total_projetos = models.IntegerField()
```

#### 2.2.4 Projeto
**Arquivo**: `v2/backend/apps/core/models/organizacao.py`

```python
class Projeto(models.Model):
    nome = models.CharField(max_length=200, unique=True)
    codigo = models.CharField(max_length=50, unique=True)
    fluxo = models.CharField()  # SUPER ou NAO_SUPER
    descricao = models.TextField()
    gerencia = models.ForeignKey(Gerencia)
    ativo = models.BooleanField()
```

**LACUNA**: Não tem campos de timing/prazos ideais

#### 2.2.5 Solicitacao
**Arquivo**: `v2/backend/apps/core/models/solicitacao.py`

```python
class Solicitacao(models.Model):
    usuario = models.ForeignKey(Usuario)
    projeto = models.ForeignKey(Projeto)
    municipio = models.ForeignKey(Municipio)
    coordenador = models.ForeignKey(Usuario)
    formadores = models.ManyToManyField(Usuario)

    inicio = models.DateTimeField()
    fim = models.DateTimeField()
    encontro = models.CharField()  # "1.0", "2.0", "3.0"... ← JÁ EXISTE!

    status = models.CharField()  # pendente/aprovado/reprovado
```

**DESCOBERTA**: O campo `encontro` já captura o número do encontro!

### 2.3 Infraestrutura Existente

| Componente | Status | Detalhes |
|------------|--------|----------|
| Celery + Redis | ✅ | Configurado para tasks assíncronas |
| Celery Beat | ✅ | Agendamento de tasks periódicas |
| AuditLog | ✅ | Registro de ações |
| Config Model | ✅ | Configurações dinâmicas |
| Structured Logging | ✅ | MP2 implementado |
| Email Backend | ❌ | Não configurado |

### 2.4 Dados Existentes no Banco

**Projetos**: ~20 projetos ativos (SUPER e NAO_SUPER)

**Valores de `encontro` em Solicitacao**:
- 1.0: 1,277 solicitações
- 2.0: 1,065 solicitações
- 3.0: 744 solicitações
- 4.0: 523 solicitações
- (continua...)

**Gerências**: 7 definidas, mas **gerente não atribuído**

**EquipeGerencia**: Estrutura existe, mas **está vazia**

---

## 3. O que Precisa Ser Criado

### 3.1 Novos Modelos

#### 3.1.1 EtapaProjeto
Define os prazos ideais para cada projeto.

```python
class EtapaProjeto(models.Model):
    projeto = models.ForeignKey(Projeto, related_name='etapas')
    ordem = models.PositiveIntegerField()  # 0=Contato, 1=1ºEnc, 2=2ºEnc...
    nome = models.CharField(max_length=100)

    # Timing - DIAS A PARTIR DO CONTATO
    dias_limite_apos_contato = models.PositiveIntegerField()
    dias_alerta_antes = models.PositiveIntegerField(default=7)

    # Escalação em cascata
    dias_escalar_coordenador = models.PositiveIntegerField(default=3)
    dias_escalar_gerente = models.PositiveIntegerField(default=5)

    class Meta:
        ordering = ['projeto', 'ordem']
        unique_together = ['projeto', 'ordem']
```

#### 3.1.2 CicloFormacao
Rastreia um ciclo completo de formação.

```python
class CicloFormacao(models.Model):
    STATUS_CHOICES = [
        ('EM_ANDAMENTO', 'Em andamento'),
        ('CONCLUIDO', 'Concluído'),
        ('CONCLUIDO_ATRASO', 'Concluído com atraso'),
        ('CANCELADO', 'Cancelado'),
    ]

    projeto = models.ForeignKey(Projeto)
    municipio = models.ForeignKey(Municipio)
    ano = models.PositiveIntegerField()

    # Responsáveis
    formador_principal = models.ForeignKey(Usuario, null=True)
    coordenador = models.ForeignKey(Usuario, null=True)

    # PONTO ZERO
    data_contato_municipio = models.DateField()  # Dia 0

    # Status
    etapa_atual = models.ForeignKey(EtapaProjeto, null=True)
    status = models.CharField(choices=STATUS_CHOICES)

    # Métricas
    data_conclusao = models.DateField(null=True)
    duracao_total_dias = models.PositiveIntegerField(null=True)
    dias_atraso_acumulado = models.IntegerField(default=0)
    percentual_conclusao = models.DecimalField(default=0)

    class Meta:
        unique_together = ['projeto', 'municipio', 'ano']
```

#### 3.1.3 EtapaRealizada
Histórico de cada etapa realizada.

```python
class EtapaRealizada(models.Model):
    STATUS_CHOICES = [
        ('PENDENTE', 'Pendente'),
        ('AGENDADA', 'Agendada'),
        ('REALIZADA', 'Realizada'),
        ('ATRASADA', 'Atrasada'),
    ]

    ciclo = models.ForeignKey(CicloFormacao, related_name='etapas_realizadas')
    etapa = models.ForeignKey(EtapaProjeto)
    solicitacao = models.ForeignKey(Solicitacao, null=True)

    # Datas
    data_prevista = models.DateField()
    data_realizada = models.DateField(null=True)

    # Métricas
    dias_desde_contato = models.PositiveIntegerField(null=True)
    dias_atraso = models.IntegerField(default=0)
    status = models.CharField(choices=STATUS_CHOICES)

    class Meta:
        unique_together = ['ciclo', 'etapa']
```

#### 3.1.4 Notification
Notificações geradas pelo sistema.

```python
class Notification(models.Model):
    TIPO_CHOICES = [
        ('ETAPA_PROXIMA', 'Próxima etapa se aproximando'),
        ('ETAPA_ATRASADA', 'Etapa atrasada'),
        ('ESCALACAO_COORDENADOR', 'Escalado para coordenador'),
        ('ESCALACAO_GERENTE', 'Escalado para gerente'),
        ('CICLO_CONCLUIDO', 'Ciclo de formações concluído'),
    ]

    NIVEL_CHOICES = [
        ('FORMADOR', 'Formador'),
        ('COORDENADOR', 'Coordenador'),
        ('GERENTE', 'Gerente'),
    ]

    usuario = models.ForeignKey(Usuario)
    tipo = models.CharField(choices=TIPO_CHOICES)
    nivel_cascata = models.CharField(choices=NIVEL_CHOICES)

    titulo = models.CharField(max_length=200)
    mensagem = models.TextField()

    # Referências
    ciclo = models.ForeignKey(CicloFormacao, null=True)
    etapa = models.ForeignKey(EtapaProjeto, null=True)

    # Status
    lida = models.BooleanField(default=False)
    lida_em = models.DateTimeField(null=True)
    acao_tomada = models.BooleanField(default=False)

    created_at = models.DateTimeField(auto_now_add=True)
```

### 3.2 Novos Services

- `timing_service.py` - Cálculo de prazos e verificação
- `notification_service.py` - Criação e gestão de notificações
- `notification_cascade_service.py` - Lógica de escalação

### 3.3 Novas Tasks Celery

- `task_verificar_prazos_diario` - Executa às 8h
- `task_atualizar_metricas_ciclos` - Atualiza estatísticas

### 3.4 Novas APIs

- `GET /api/notifications/` - Lista notificações do usuário
- `GET /api/notifications/unread-count/` - Contador de não lidas
- `POST /api/notifications/{id}/mark-read/` - Marca como lida
- `POST /api/notifications/mark-all-read/` - Marca todas
- `GET /api/ciclos/` - Lista ciclos de formação
- `GET /api/ciclos/dashboard/` - Dashboard de métricas
- `GET /api/ciclos/{id}/` - Detalhe de um ciclo

### 3.5 Novos Componentes Frontend

- `NotificationBell.jsx` - Ícone no header com badge
- `NotificationDrawer.jsx` - Drawer lateral com lista
- `NotificationItem.jsx` - Item individual
- `CiclosDashboard.jsx` - Dashboard de ciclos (opcional)

---

## 4. Fluxo de Dados Proposto

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         FLUXO DE DADOS                                  │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  1. ENTRADA DE DADOS (Páginas existentes)                              │
│  ─────────────────────────────────────────                             │
│                                                                         │
│  /dat-module/acoes                                                      │
│       │                                                                 │
│       ├─→ DATAcao.data_contato = "Dia 0"                               │
│       │                                                                 │
│       └─→ Signal: criar CicloFormacao se não existir                   │
│                                                                         │
│  /dat-module/formacoes ou /solicitacoes/nova                           │
│       │                                                                 │
│       ├─→ DATFormacao ou Solicitacao com encontro="1.0", "2.0"...      │
│       │                                                                 │
│       └─→ Signal: criar/atualizar EtapaRealizada                       │
│                                                                         │
│  2. PROCESSAMENTO (Celery Beat - 8h diário)                            │
│  ──────────────────────────────────────────                            │
│                                                                         │
│  task_verificar_prazos_diario()                                        │
│       │                                                                 │
│       ├─→ Para cada CicloFormacao ativo:                               │
│       │       │                                                         │
│       │       ├─→ Calcular dias desde contato                          │
│       │       ├─→ Verificar próxima etapa pendente                     │
│       │       ├─→ Comparar com EtapaProjeto.dias_limite                │
│       │       │                                                         │
│       │       └─→ Se próximo do prazo ou atrasado:                     │
│       │               │                                                 │
│       │               └─→ Criar Notification (nível apropriado)        │
│       │                                                                 │
│       └─→ Evitar duplicatas (1 notificação/dia/etapa/nível)           │
│                                                                         │
│  3. SAÍDA (Frontend)                                                    │
│  ───────────────────                                                   │
│                                                                         │
│  NotificationBell (Header)                                              │
│       │                                                                 │
│       ├─→ Badge com count de não lidas                                 │
│       │                                                                 │
│       └─→ Ao clicar: NotificationDrawer                                │
│               │                                                         │
│               ├─→ Lista de notificações                                │
│               ├─→ Ação: Marcar como lida                               │
│               └─→ Ação: Ir para /solicitacoes/nova                     │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## 5. Lógica de Cascata

```python
def determinar_nivel_notificacao(ciclo, etapa, dias_atraso):
    """
    Determina quem deve ser notificado baseado no atraso.

    Níveis:
    - FORMADOR: Alerta inicial (prazo se aproximando ou início do atraso)
    - COORDENADOR: Escalação após N dias sem ação
    - GERENTE: Escalação final após M dias sem ação
    """

    # Verificar se já existe solicitação para esta etapa
    tem_solicitacao = Solicitacao.objects.filter(
        projeto=ciclo.projeto,
        municipio=ciclo.municipio,
        encontro=str(etapa.ordem),
        status__in=['pendente', 'aprovado']
    ).exists()

    if tem_solicitacao:
        return None  # Ação já foi tomada

    # Determinar nível baseado no atraso
    if dias_atraso <= 0:
        # Prazo ainda não passou, mas está próximo
        return 'FORMADOR'
    elif dias_atraso <= etapa.dias_escalar_coordenador:
        # Atrasado, mas dentro da janela do formador
        return 'FORMADOR'
    elif dias_atraso <= etapa.dias_escalar_gerente:
        # Passou janela do formador, escalar para coordenador
        return 'COORDENADOR'
    else:
        # Passou todas as janelas, escalar para gerente
        return 'GERENTE'
```

---

## 6. Informações Pendentes

### 6.1 Dados de Configuração (aguardando usuário)

| Informação | Status | Exemplo Esperado |
|------------|--------|------------------|
| Prazos por projeto | ⏳ Aguardando | TEMA: 1º=15d, 2º=45d, 3º=75d |
| Quantidade de encontros por projeto | ⏳ Aguardando | TEMA: 4, ACerta: 3 |
| Hierarquia de equipes | ⏳ Aguardando | Gerentes por gerência |
| Tempos de escalação | ⏳ Aguardando | Coord: 3d, Gerente: 5d |

### 6.2 Decisões Pendentes

| Decisão | Opções | Recomendação |
|---------|--------|--------------|
| Dia 0 | `data_contato` ou `data_reuniao` | `data_contato` |
| Canal | In-App, Email, WhatsApp | In-App (fase 1) |
| Frequência da task | 1x/dia, 2x/dia | 1x/dia às 8h |

---

## 7. Referências de Arquivos

### 7.1 Backend

| Arquivo | Conteúdo |
|---------|----------|
| `apps/core/models/workflow.py` | DATAcao |
| `apps/core/models/organizacao.py` | Projeto, Gerencia |
| `apps/core/models/solicitacao.py` | Solicitacao |
| `apps/core/models/usuario.py` | Usuario |
| `apps/core/views/dat_module.py` | Views do DAT Module |
| `apps/core/tasks.py` | Tasks Celery existentes |
| `config/settings.py` | Configurações Celery |

### 7.2 Frontend

| Arquivo | Conteúdo |
|---------|----------|
| `src/App.jsx` | Rotas e layout principal |
| `src/pages/DATModule/AcoesPage.jsx` | Página de ações |
| `src/pages/DATModule/FormacoesPage.jsx` | Página de formações |
| `src/pages/DATModule/CoordenadoresPage.jsx` | Página de coordenadores |
| `src/api/datModule.js` | API do DAT Module |

---

## 8. Changelog

| Data | Versão | Mudanças |
|------|--------|----------|
| 2025-12-19 | 1.0 | Análise inicial completa |

---

**Autor**: Claude Code
**Projeto**: Aprender Sistema v2
