# 🔍 AUDITORIA TÉCNICA COMPLETA - SISTEMA APRENDER

**Data**: 02/10/2025
**Auditor**: Claude Code (Sonnet 4.5)
**Escopo**: Validação pós-Dias 1-3 + Hotfix Dia 3 + Pre-commit Hardening
**Objetivo**: Garantir alinhamento 100% com mudanças canônicas antes da importação de dados reais

---

## 📊 RESUMO EXECUTIVO

### ✅ STATUS GERAL: **PARCIALMENTE APROVADO COM ALERTAS CRÍTICOS**

- **Infraestrutura**: ✅ PASS (100%)
- **Backend Django/DRF**: ⚠️ WARN (85% - inconsistências encontradas)
- **Hotfix Dia 3**: ❌ FAIL (comandos canônicos não encontrados)
- **Frontend React**: ⚠️ WARN (50% - implementação mínima)
- **Templates Django**: ❌ FAIL (referências PRE_AGENDA extensivas)
- **Higiene de Código**: ❌ FAIL (FormadoresSolicitacao widespread)

---

## 📋 MATRIZ PASS/FAIL POR CRITÉRIO

### (A) INFRAESTRUTURA

| Critério | Status | Evidência |
|----------|--------|-----------|
| Docker Compose version | ✅ PASS | v2.39.4-desktop.1 |
| Stack correta | ✅ PASS | `com.docker.compose.project: aprendersistema` |
| Containers running | ✅ PASS | 4/4 containers Up (db, web, redis, frontend) |
| Container web healthy | ✅ PASS | Up 6 minutes (healthy) |
| `/api/health/` responde 200 | ✅ PASS | HTTP/1.1 200 OK |

**Evidências**:
```
Docker version 28.4.0, build d8eb465
Docker Compose version v2.39.4-desktop.1

NAME                            STATUS
aprender_db_development         Up 12 hours (healthy)
aprender_frontend_development   Up 12 hours
aprender_redis_development      Up 12 hours (healthy)
aprender_web_development        Up 6 minutes (healthy)

HTTP/1.1 200 OK
Content-Type: application/json
```

---

### (B) BACKEND DJANGO / DRF

| Critério | Status | Evidência |
|----------|--------|-----------|
| Django check | ✅ PASS | System check identified no issues |
| Migrations 0032-0035 aplicadas | ✅ PASS | Todas [X] aplicadas |
| MarcadorPlanilha campos canônicos | ✅ PASS | external_hash, origem_aba, gid, linha, cancelado_flag ✓ |
| SolicitacaoStatus enum correto | ✅ PASS | [AGENDADO, APROVADO, CANCELADO, CRIADO, REALIZADO] |
| PRE_AGENDA removido do enum | ✅ PASS | Não presente no enum |
| CONCLUIDO removido do enum | ✅ PASS | Não presente no enum |
| Admin: 4 canônicos registrados | ✅ PASS | VinculoUsuarioSetor, Participante, MarcadorPlanilha, AprovacaoHistorico ✓ |
| EventoGoogleCalendar no admin | ✅ PASS | Registrado |
| API root `/api/` funcional | ✅ PASS | JSON com endpoints v1 |
| API v1 requer auth | ✅ PASS | 401 sem credenciais |
| Usuario related_names corretos | ✅ PASS | grupos='usuarios', user_permissions='usuarios' |

**Evidências de Migrations**:
```
[X] 0032_add_canonical_models_and_fields
[X] 0033_status_rename
[X] 0034_add_origem_to_aprovacao_historico_hotfix_dia3
[X] 0035_add_origem_to_marcador_planilha
```

**MarcadorPlanilha fields**:
```python
['cancelado_flag', 'created_at', 'disponibilidade', 'external_hash', 'gid',
 'id', 'linha', 'origem', 'origem_aba', 'remarcado_de', 'remarcado_para',
 'solicitacao', 'updated_at']
```

**SolicitacaoStatus enum**:
```python
Status choices: ['AGENDADO', 'APROVADO', 'CANCELADO', 'CRIADO', 'REALIZADO']
```

**Admin models registrados**:
```python
['Usuario', 'Projeto', 'Municipio', 'TipoEvento', 'Solicitacao', 'Aprovacao',
 'EventoGoogleCalendar', 'DisponibilidadeFormadores', 'LogAuditoria', 'Deslocamento',
 'VinculoUsuarioSetor', 'Participante', 'MarcadorPlanilha', 'AprovacaoHistorico']
```

---

### (C) HOTFIX DIA 3 / INGESTÃO

| Critério | Status | Evidência |
|----------|--------|-----------|
| `import_usuarios` existe | ❌ FAIL | Comando não encontrado |
| `import_eventos_abas` existe | ❌ FAIL | Comando não encontrado |
| `import_disponibilidades_sheets` existe | ❌ FAIL | Comando não encontrado |
| `backend.config.sheets_config` importável | ✅ PASS | OK com 4 IDs |
| Diretório `ingestao/` existe | ✅ PASS | Presente mas vazio |
| Padrões hotfix em código | ❌ FAIL | Nenhum padrão encontrado |

**Evidências - Comandos disponíveis**:
```
import_aba_super
import_acerta_colunas_e_t
import_agenda_completa
import_agenda_completa_tratada
import_brincando_colunas_e_t
import_dados_extraidos
import_disponibilidades
import_extracted_events
import_google_sheets
import_municipios
import_organizational_structure
import_outros_colunas_e_t
import_projetos
import_super_colunas_e_t
import_tipos_evento
import_vidas_colunas_e_t
```

**sheets_config.py**:
```python
sheets_config OK; keys: ['AGENDA_2025_ID', 'CONTROLE_2025_ID', 'DISPONIBILIDADE_2025_ID', 'USUARIOS_ID']
```

**🚨 ANÁLISE CRÍTICA**:
- **PROBLEMA**: Comandos canônicos especificados no Hotfix Dia 3 não existem
- **ENCONTRADO**: 16 comandos de importação legados com nomenclatura antiga
- **RISCO**: Sistema ainda usa comandos antigos (`import_google_sheets`, `import_aba_super`, etc.)
- **IMPACTO**: Alto - importação real pode falhar ou criar dados inconsistentes

---

### (D) SEGURANÇA & CONFIG

| Critério | Status | Evidência |
|----------|--------|-----------|
| Usuario.groups related_name | ✅ PASS | 'usuarios' |
| Usuario.user_permissions related_name | ✅ PASS | 'usuarios' |
| MCP_TOOLS_ENABLED | ✅ PASS | True |
| MCP_DEBUG_MODE | ✅ PASS | True |

---

### (E) HIGIENE DE CÓDIGO

| Critério | Status | Evidência |
|----------|--------|-----------|
| PRE_AGENDA em código | ❌ FAIL | 108+ ocorrências encontradas |
| CONCLUIDO em código | ⚠️ WARN | 2 ocorrências (migrate_formacoes.py) |
| FormadoresSolicitacao referências | ❌ FAIL | 87+ ocorrências (widespread) |
| dockerDesktopLinuxEngine | ✅ PASS | Não encontrado |
| "datsu" hardcoded | ✅ PASS | Não encontrado |

**🚨 DETALHAMENTO - PRE_AGENDA (108+ ocorrências)**:

**Templates Django** (CRÍTICO):
- `core/templates/core/base.html`: Link menu "controle_pre_agenda"
- `core/templates/core/controle/pre_agenda.html`: Template completo (6 ocorrências)
- `core/templates/core/home.html`: Link menu pré-agenda

**Views** (CRÍTICO - Lógica de Negócio):
- `core/views/controle_pre_agenda_views.py`: 8 ocorrências (view dedicada)
- `core/views/solicitacao_views.py`: Linha 45 - atribui PRE_AGENDA
- `core/views/aprovacao_views.py`: Linhas 108, 137, 154
- `core/views/mapa_views.py`: 4 ocorrências em filtros
- `core/views/mapa_realtime_views.py`: 3 ocorrências
- `core/views/api_calendar.py`: 7 ocorrências (validações críticas)
- `core/views/api_approval.py`: Linha 119 - atribui PRE_AGENDA

**API/Serializers** (MÉDIO):
- `api/views.py`: Linhas 220, 394 - filtros usando PRE_AGENDA

**MCP Toolsets** (MÉDIO):
- `core/mcp/toolsets/solicitacao_toolset.py`: Linha 269

**Management Commands** (MÉDIO):
- `core/management/commands/calendar_check.py`: 2 ocorrências
- `core/management/commands/create_sample_data.py`: Linha 260

**Documentação** (BAIXO):
- CHANGELOG.md, CLAUDE.md, docs/ (múltiplas referências históricas)

**🚨 DETALHAMENTO - FormadoresSolicitacao (87+ ocorrências)**:

**Models** (CRÍTICO):
- `core/models.py`: Linhas 846-866 - classe completa ainda existe
- **NOTA**: Modelo Participante (linhas 883-903) convive com FormadoresSolicitacao

**Serializers/API**:
- `api/serializers.py`: Linhas 16, 138, 144, 185 - serializer dedicado

**Views**:
- `core/views/base.py`: Linha 71 - importa FormadoresSolicitacao
- `core/views/diretoria_views.py`: Linha 266 - usa FormadoresSolicitacao

**Admin**:
- `core/admin.py`: Linhas 10, 98, 99, 117 - inline dedicado

**Management Commands** (EXTENSIVO):
- `import_dados_extraidos.py`: Linhas 22, 429
- `import_brincando_colunas_e_t.py`: Linhas 38, 539, 541
- `import_agenda_completa.py`: Linhas 33, 527
- `import_acerta_colunas_e_t.py`: Linhas 38, 539, 541
- `import_vidas_colunas_e_t.py`: Linhas 38, 539, 541
- E mais 10+ comandos

**Scripts Auxiliares**:
- `create_sample_data.py`: Linhas 21, 41, 120
- `dashboard_streamlit.py`: Linhas 29, 155
- `test_dashboard_final.py`: 5 ocorrências

---

### (F) FRONTEND REACT

| Critério | Status | Evidência |
|----------|--------|-----------|
| Container frontend existe e Up | ✅ PASS | Up 12 hours |
| Node.js version | ✅ PASS | v20.19.5 |
| npm version | ✅ PASS | 10.8.2 |
| package.json existe | ✅ PASS | Sim |
| React instalado | ✅ PASS | ^18.2.0 |
| react-router-dom instalado | ✅ PASS | ^6.20.0 |
| TypeScript instalado | ✅ PASS | ^4.9.5 |
| Axios instalado | ✅ PASS | ^1.6.0 |
| Rotas implementadas | ❌ FAIL | Nenhuma rota (apenas App.tsx básico) |
| Chamadas API v1 | ❌ FAIL | Apenas /api/health/ hardcoded |
| Componentes de negócio | ❌ FAIL | Nenhum componente criado |
| PRE_AGENDA no frontend | ✅ PASS | Não encontrado |
| CONCLUIDO no frontend | ✅ PASS | Não encontrado |

**Estrutura frontend**:
```
src/
├── App.tsx           (66 linhas - apenas healthcheck)
├── index.tsx         (boilerplate)
└── react-app-env.d.ts
```

**App.tsx análise**:
```typescript
// Único fetch: hardcoded para localhost:8000/api/health/
fetch('http://localhost:8000/api/health/')

// Conteúdo: página de status básica
// SEM: rotas, componentes, integração com /api/v1/, autenticação
```

**🚨 ANÁLISE CRÍTICA**:
- **STATUS**: Frontend é esqueleto de demonstração
- **IMPLEMENTAÇÃO**: ~5% (apenas prova de conceito)
- **RISCO**: Alto - usuários não têm interface funcional
- **FALTAM**: Todas as telas de negócio (Solicitações, Aprovações, Agenda, etc.)

---

### (G) TEMPLATES DJANGO

| Critério | Status | Evidência |
|----------|--------|-----------|
| Diretório templates/ existe | ✅ PASS | core/templates/ |
| Total de templates | ✅ PASS | 50+ templates |
| PRE_AGENDA em templates | ❌ FAIL | 10 ocorrências em 3 arquivos críticos |
| CONCLUIDO em templates | ⚠️ WARN | 1 ocorrência (relatorios.html) |
| FormadoresSolicitacao em templates | ✅ PASS | Não encontrado |

**Templates com PRE_AGENDA**:
1. `core/templates/core/base.html` - Link menu "Pré-Agenda"
2. `core/templates/core/controle/pre_agenda.html` - Template completo dedicado
3. `core/templates/core/home.html` - Link menu pré-agenda

**Templates existentes (parcial)**:
```
core/templates/core/
├── admin/
│   └── communication_logs.html
├── aprovacao_detail.html
├── aprovacoes_pendentes_enhanced.html
├── base.html ⚠️ (menu PRE_AGENDA)
├── bloqueio_form.html
├── bloqueio_ok.html
├── controle/
│   ├── auditoria_log.html
│   ├── google_calendar_monitor.html
│   └── pre_agenda.html ❌ (template completo PRE_AGENDA)
├── coordenador/
│   └── meus_eventos.html
├── deslocamentos/ (form, list, delete)
├── diretoria/
│   ├── dashboard_working_original.html
│   └── relatorios.html ⚠️ (projetos_concluidos)
├── formador_eventos.html
├── gestao/ (formadores, municipios, projetos, tipos_evento)
├── home.html ⚠️ (link PRE_AGENDA)
└── mapa_mensal_view.html
```

---

## 🗺️ INVENTÁRIO DE ROTAS/TELAS

### Backend Django (URLs)

**API REST (`/api/v1/`)**:
```python
✅ /api/health/                 # Healthcheck
✅ /api/v1/usuarios/            # CRUD Usuários
✅ /api/v1/projetos/            # CRUD Projetos
✅ /api/v1/municipios/          # CRUD Municípios
✅ /api/v1/tipos-evento/        # CRUD Tipos de Evento
✅ /api/v1/formadores/          # Lista Formadores
✅ /api/v1/solicitacoes/        # CRUD Solicitações ⚠️ (usa FormadoresSolicitacao)
✅ /api/v1/aprovacoes/          # CRUD Aprovações
✅ /api/v1/eventos-google/      # CRUD Eventos Google Calendar
✅ /api/v1/disponibilidade/     # Disponibilidade formadores
✅ /api/v1/logs-auditoria/      # Logs de auditoria
✅ /api/v1/estatisticas/        # Estatísticas gerais
✅ /api/auth/token/             # Autenticação JWT
✅ /api/auth/login/             # Login
```

**Templates Django (estimado de core/urls.py)**:
```python
✅ /                            # Home
✅ /solicitar/                  # Solicitação de eventos ⚠️ (pode usar PRE_AGENDA)
✅ /aprovacoes/pendentes/       # Aprovações pendentes
✅ /aprovacao/<id>/             # Detalhe aprovação
✅ /bloqueios/novo/             # Criar bloqueio
✅ /bloqueios/ok/               # Confirmação bloqueio
❌ /controle/pre-agenda/        # Pré-agenda (ROTA LEGADA)
✅ /controle/auditoria/         # Auditoria
✅ /controle/calendar-monitor/  # Monitor Google Calendar
✅ /coordenador/eventos/        # Meus eventos (coordenador)
✅ /deslocamentos/              # CRUD Deslocamentos
✅ /diretoria/dashboard/        # Dashboard diretoria
✅ /diretoria/relatorios/       # Relatórios
✅ /formador/eventos/           # Eventos formador
✅ /gestao/formadores/          # CRUD Formadores
✅ /gestao/municipios/          # CRUD Municípios
✅ /gestao/projetos/            # CRUD Projetos
✅ /gestao/tipos-evento/        # CRUD Tipos de Evento
✅ /mapa-mensal/                # Mapa de disponibilidade
```

### Frontend React (URLs)

**Rotas implementadas**:
```
❌ NENHUMA ROTA IMPLEMENTADA

Apenas:
/ - App.tsx (healthcheck page)
```

**Rotas esperadas (não implementadas)**:
```
❌ /login
❌ /dashboard
❌ /solicitacoes
❌ /solicitacoes/nova
❌ /solicitacoes/:id
❌ /aprovacoes
❌ /aprovacoes/:id
❌ /agenda
❌ /calendario
❌ /relatorios
❌ /configuracoes
```

---

## ⚠️ RISCOS ANTES DA IMPORTAÇÃO REAL

### 🔴 CRÍTICOS (Bloqueadores)

1. **PRE_AGENDA extensivo em views/templates**
   - **Risco**: Importação de dados pode atribuir status PRE_AGENDA
   - **Impacto**: Dados inconsistentes com enum canônico
   - **Localização**: 108+ ocorrências
   - **Bloqueador**: Sim - violação do enum

2. **FormadoresSolicitacao coexiste com Participante**
   - **Risco**: Confusão entre modelos antigos e canônicos
   - **Impacto**: Relacionamentos duplicados/inconsistentes
   - **Localização**: 87+ ocorrências (código ativo)
   - **Bloqueador**: Sim - modelo legado em uso

3. **Comandos de importação canônicos ausentes**
   - **Risco**: Importação real usará comandos legados
   - **Impacto**: Regras hotfix não aplicadas (derive_status, cancelado_flag, etc.)
   - **Esperado**: `import_usuarios`, `import_eventos_abas`, `import_disponibilidades_sheets`
   - **Encontrado**: 16 comandos legados com nomenclatura antiga
   - **Bloqueador**: Sim - spec Hotfix Dia 3 não implementada

4. **Rota /controle/pre-agenda/ ativa**
   - **Risco**: Usuários podem acessar funcionalidade deprecated
   - **Impacto**: Criação de eventos com status inválido
   - **Bloqueador**: Sim - viola enum canônico

### 🟡 ALTOS (Preocupantes)

5. **Views atribuem PRE_AGENDA programaticamente**
   - **Arquivos**: `solicitacao_views.py:45`, `api_approval.py:119`
   - **Risco**: Código executável cria dados inválidos
   - **Impacto**: Banco de dados com status que não existe no enum

6. **API views filtram por PRE_AGENDA**
   - **Arquivos**: `api/views.py:220,394`
   - **Risco**: Queries retornam vazio ou falham
   - **Impacto**: Dashboard/estatísticas quebrados

7. **Serializers usam FormadoresSolicitacao**
   - **Arquivo**: `api/serializers.py`
   - **Risco**: API retorna estrutura antiga
   - **Impacto**: Frontend/integraçõesrecebem dados legados

8. **Templates exibem rótulos antigos**
   - **Risco**: UX confusa para usuários
   - **Impacto**: Experiência inconsistente

### 🟢 MÉDIOS (Monitoráveis)

9. **Frontend React não implementado**
   - **Risco**: Usuários dependem de templates Django
   - **Impacto**: UX subótima, SPA não utilizável
   - **Mitigação**: Templates Django funcionais

10. **CONCLUIDO em migrate_formacoes.py**
    - **Arquivo**: `core/management/commands/migrate_formacoes.py:308`
    - **Risco**: Migration histórica pode criar dados legados
    - **Impacto**: Baixo (comando provavelmente não usado)

11. **Documentação desatualizada**
    - **Risco**: Desenvolvedores seguem docs antigos
    - **Impacto**: Médio - confusão de contexto

---

## 🔧 PATCHES PROPOSTOS

### PATCH 1: Remover PRE_AGENDA de Views

**Arquivo**: `core/views/solicitacao_views.py`

```diff
--- a/core/views/solicitacao_views.py
+++ b/core/views/solicitacao_views.py
@@ -42,7 +42,7 @@ class SolicitacaoCreateView(CreateView):
                 # Lógica de aprovação automática ou manual
                 if self.object.requer_aprovacao():
-                    solicitacao.status = SolicitacaoStatus.PRE_AGENDA
+                    solicitacao.status = SolicitacaoStatus.CRIADO
                 else:
                     solicitacao.status = SolicitacaoStatus.APROVADO
```

**Arquivo**: `core/views/api_approval.py`

```diff
--- a/core/views/api_approval.py
+++ b/core/views/api_approval.py
@@ -116,7 +116,7 @@ class ApprovalAPIView(APIView):
             if acao == "aprovar":
-                novo_status = SolicitacaoStatus.PRE_AGENDA
+                novo_status = SolicitacaoStatus.APROVADO
             elif acao == "reprovar":
                 novo_status = SolicitacaoStatus.CANCELADO
```

### PATCH 2: Remover Filtros PRE_AGENDA de API

**Arquivo**: `api/views.py`

```diff
--- a/api/views.py
+++ b/api/views.py
@@ -217,7 +217,7 @@ class EventosView(APIView):
         # Filtrar eventos por status
         eventos = Solicitacao.objects.filter(
-            status__in=["PRE_AGENDA", "APROVADO"]
+            status__in=[SolicitacaoStatus.APROVADO, SolicitacaoStatus.AGENDADO]
         )

@@ -391,7 +391,7 @@ class EstatisticasView(APIView):
         # Estatísticas de aprovações
-        aprovadas = Solicitacao.objects.filter(status="PRE_AGENDA").count()
+        aprovadas = Solicitacao.objects.filter(status=SolicitacaoStatus.APROVADO).count()
```

### PATCH 3: Desabilitar Rota PRE_AGENDA

**Arquivo**: `core/urls.py` (estimado)

```diff
--- a/core/urls.py
+++ b/core/urls.py
@@ -50,8 +50,8 @@ urlpatterns = [
     # Controle
-    path('controle/pre-agenda/', ControlePreAgendaView.as_view(), name='controle_pre_agenda'),
-    path('controle/pre-agenda/criar/', CriarEventoGoogleCalendarView.as_view(), name='criar_evento_google'),
-    path('controle/pre-agenda/remover/<uuid:pk>/', RemoverEventoPreAgendaView.as_view(), name='remover_evento_pre_agenda'),
+    # path('controle/pre-agenda/', ControlePreAgendaView.as_view(), name='controle_pre_agenda'),  # DEPRECATED
+    # path('controle/pre-agenda/criar/', CriarEventoGoogleCalendarView.as_view(), name='criar_evento_google'),  # DEPRECATED
+    # path('controle/pre-agenda/remover/<uuid:pk>/', RemoverEventoPreAgendaView.as_view(), name='remover_evento_pre_agenda'),  # DEPRECATED
```

### PATCH 4: Remover Links PRE_AGENDA de Templates

**Arquivo**: `core/templates/core/base.html`

```diff
--- a/core/templates/core/base.html
+++ b/core/templates/core/base.html
@@ -467,7 +467,7 @@
           <!-- Controle -->
-          <a href="{% url 'core:controle_pre_agenda' %}" class="nav-item {% block nav_controle_pre_agenda %}{% endblock %}">
-            <i class="fas fa-calendar-plus"></i> Pré-Agenda
-          </a>
+          <!-- Link Pré-Agenda removido (status deprecated) -->
```

**Arquivo**: `core/templates/core/home.html`

```diff
--- a/core/templates/core/home.html
+++ b/core/templates/core/home.html
@@ -417,7 +417,7 @@
         <div class="quick-links">
-          <a href="{% url 'core:controle_pre_agenda' %}" class="nav-item">
-            <i class="fas fa-calendar-plus"></i> Pré-Agenda
-          </a>
+          <!-- Link Pré-Agenda removido (status deprecated) -->
```

### PATCH 5: Deprecar FormadoresSolicitacao (Gradual)

**Arquivo**: `core/models.py`

```diff
--- a/core/models.py
+++ b/core/models.py
@@ -844,6 +844,11 @@ class Solicitacao(models.Model):


 class FormadoresSolicitacao(models.Model):
+    """
+    DEPRECATED: Use Participante com papel='FORMADOR' ao invés deste modelo.
+    Mantido temporariamente para compatibilidade com código legado.
+    TODO: Migrar todos os usos para Participante e remover este modelo.
+    """
     solicitacao = models.ForeignKey(Solicitacao, on_delete=models.CASCADE)
     # Alterado para Usuario com filtro por grupo formador
```

**Arquivo**: `api/serializers.py`

```diff
--- a/api/serializers.py
+++ b/api/serializers.py
@@ -13,7 +13,7 @@ from core.models import (
     Usuario,
-    FormadoresSolicitacao,
+    Participante,
 )


@@ -135,12 +135,12 @@ class UsuarioSerializer(serializers.ModelSerializer):
         ]


-class FormadoresSolicitacaoSerializer(serializers.ModelSerializer):
+class ParticipanteSerializer(serializers.ModelSerializer):
     """
-    Serializer para o relacionamento Formador-Solicitação.
+    Serializer para o relacionamento Participante-Solicitação.
     """

-    formador_nome = serializers.CharField(source="usuario.nome_completo", read_only=True)
+    usuario_nome = serializers.CharField(source="usuario.nome_completo", read_only=True)

     class Meta:
-        model = FormadoresSolicitacao
-        fields = ["id", "solicitacao", "usuario", "formador_nome"]
+        model = Participante
+        fields = ["id", "solicitacao", "usuario", "usuario_nome", "papel"]
```

### PATCH 6: Criar Comandos Canônicos de Importação

**Novo arquivo**: `core/management/commands/ingestao/import_usuarios.py`

```python
"""
Comando canônico para importação de usuários.
Implementa regras do Hotfix Dia 3:
- usuario.origem='planilha'
- usuario.is_provisorio=True
- Nunca sobrescreve usuários existentes
"""
from django.core.management.base import BaseCommand
from core.models import Usuario


class Command(BaseCommand):
    help = "Importa usuários da planilha (implementação canônica Hotfix Dia 3)"

    def add_arguments(self, parser):
        parser.add_argument('--dry-run', action='store_true')
        parser.add_argument('--verbose', action='store_true')

    def handle(self, *args, **options):
        # TODO: Implementar conforme spec Hotfix Dia 3
        self.stdout.write(self.style.WARNING("Comando import_usuarios ainda não implementado"))
        pass
```

**Novo arquivo**: `core/management/commands/ingestao/import_eventos_abas.py`

```python
"""
Comando canônico para importação de eventos de abas.
Implementa regras do Hotfix Dia 3:
- derive_status com corte 25/09/2025
- Nunca setar AGENDADO durante import
- Criar AprovacaoHistorico quando Super=Aprovação SIM
- MarcadorPlanilha com origem_aba, gid, linha, cancelado_flag
- Não pular cancelados/adiados
"""
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Importa eventos de abas (implementação canônica Hotfix Dia 3)"

    def add_arguments(self, parser):
        parser.add_argument('--aba', type=str, help='Nome da aba específica')
        parser.add_argument('--dry-run', action='store_true')
        parser.add_argument('--verbose', action='store_true')

    def handle(self, *args, **options):
        # TODO: Implementar conforme spec Hotfix Dia 3
        self.stdout.write(self.style.WARNING("Comando import_eventos_abas ainda não implementado"))
        pass
```

**Novo arquivo**: `core/management/commands/ingestao/import_disponibilidades_sheets.py`

```python
"""
Comando canônico para importação de disponibilidades.
"""
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Importa disponibilidades da planilha (implementação canônica Hotfix Dia 3)"

    def add_arguments(self, parser):
        parser.add_argument('--dry-run', action='store_true')
        parser.add_argument('--verbose', action='store_true')

    def handle(self, *args, **options):
        # TODO: Implementar conforme spec Hotfix Dia 3
        self.stdout.write(self.style.WARNING("Comando import_disponibilidades_sheets ainda não implementado"))
        pass
```

---

## 📋 BACKLOG MÍNIMO PARA SPRINT SEGUINTE

### 🔴 PRIORIDADE CRÍTICA (Bloqueadores para importação)

1. **Remover PRE_AGENDA de toda a aplicação** (Estimativa: 4h)
   - Aplicar PATCH 1, 2, 3, 4
   - Remover view `controle_pre_agenda_views.py` completa
   - Remover template `core/templates/core/controle/pre_agenda.html`
   - Testar fluxo de aprovação sem PRE_AGENDA

2. **Implementar comandos canônicos de importação** (Estimativa: 16h)
   - Criar `import_usuarios` conforme Hotfix Dia 3
   - Criar `import_eventos_abas` com derive_status e regras
   - Criar `import_disponibilidades_sheets`
   - Testar importação com dados de exemplo

3. **Migração FormadoresSolicitacao → Participante** (Estimativa: 8h)
   - Criar migration de dados (FormadoresSolicitacao → Participante)
   - Atualizar serializers (aplicar PATCH 5)
   - Atualizar views/queries
   - Remover modelo FormadoresSolicitacao após validação

### 🟡 PRIORIDADE ALTA (Qualidade)

4. **Atualizar serializers/API para modelos canônicos** (Estimativa: 4h)
   - ParticipanteSerializer
   - VinculoUsuarioSetorSerializer
   - MarcadorPlanilhaSerializer
   - AprovacaoHistoricoSerializer

5. **Implementar RBAC fino com VinculoUsuarioSetor** (Estimativa: 8h)
   - Decorators/mixins para permissões por setor
   - Filtros de queryset por vínculo
   - Validações em views/serializers

6. **Remover/deprecar comandos legados** (Estimativa: 2h)
   - Marcar 16 comandos legados como deprecated
   - Documentar migração para comandos canônicos
   - Atualizar CLAUDE.md com comandos corretos

### 🟢 PRIORIDADE MÉDIA (UX)

7. **Implementar telas React** (Estimativa: 40h)
   - Sistema de rotas (react-router-dom)
   - Layout base com menu/autenticação
   - Telas de Solicitações (lista, criar, detalhe)
   - Telas de Aprovações (lista, aprovar/reprovar)
   - Tela de Agenda/Calendário
   - Tela de Relatórios

8. **Integração React ↔ API Django** (Estimativa: 8h)
   - Serviço de autenticação (JWT)
   - Serviço de API (axios configurado)
   - Estado global (Context API ou Redux)
   - Interceptors para erro/loading

9. **Atualizar documentação** (Estimativa: 4h)
   - CLAUDE.md: remover PRE_AGENDA, atualizar comandos
   - CHANGELOG.md: documentar Dia 3
   - API docs: Swagger/OpenAPI atualizado

### 🔵 PRIORIDADE BAIXA (Housekeeping)

10. **Limpar CONCLUIDO de migrate_formacoes** (Estimativa: 1h)
    - Revisar comando migrate_formacoes.py
    - Substituir por REALIZADO

11. **Remover docs/templates deprecated** (Estimativa: 2h)
    - Mover documentos históricos para `docs/archive/`
    - Limpar referências obsoletas

12. **Testes end-to-end** (Estimativa: 16h)
    - Fluxo completo: Criação → Aprovação → Agendamento
    - Teste de importação com dados reais (amostra)
    - Validação de integridade referencial

---

## 🎯 CRITÉRIOS DE ACEITAÇÃO PARA GO-LIVE

**Antes de importar dados reais, o sistema DEVE**:

1. ✅ **Zero ocorrências de PRE_AGENDA** em código executável (views/serializers/commands)
2. ✅ **Comandos canônicos implementados** (import_usuarios, import_eventos_abas, import_disponibilidades_sheets)
3. ✅ **FormadoresSolicitacao migrado** para Participante
4. ✅ **Regras Hotfix Dia 3 testadas** (derive_status, cancelado_flag, AprovacaoHistorico)
5. ✅ **API v1 funcional** com modelos canônicos
6. ⚠️ **Frontend React básico** OU Templates Django completos (pelo menos 1 opção)
7. ✅ **Healthcheck 200** e containers healthy
8. ✅ **Migrations 0032-0035 aplicadas** em produção
9. ✅ **Backup de dados** antes da importação
10. ✅ **Rollback plan** documentado

---

## 📝 CONCLUSÃO

### Veredito: **NÃO PRONTO PARA IMPORTAÇÃO DE DADOS REAIS**

**Motivos**:
1. **PRE_AGENDA**: 108+ ocorrências em código ativo que podem criar dados inválidos
2. **Comandos canônicos**: Não implementados conforme spec Hotfix Dia 3
3. **FormadoresSolicitacao**: Modelo legado coexiste com Participante (87+ ocorrências)
4. **Frontend**: Não implementado (apenas esqueleto)

**Pontos Positivos**:
- Infraestrutura Docker 100% operacional
- Migrations canônicas aplicadas corretamente
- Enum SolicitacaoStatus limpo (sem PRE_AGENDA/CONCLUIDO)
- Backend Django/DRF estruturado
- API healthcheck funcional

**Ação Recomendada**:
1. **PARAR**: Não importar dados reais ainda
2. **EXECUTAR**: Backlog Prioridade Crítica (itens 1-3)
3. **TESTAR**: Importação com amostra pequena (~10 registros)
4. **VALIDAR**: Critérios de aceitação
5. **ENTÃO**: Importação completa

**Estimativa para Prontidão**: 28-32 horas de desenvolvimento + 8 horas de testes

---

**Assinatura Digital**: Claude Code - Sonnet 4.5
**Timestamp**: 2025-10-02T12:45:00Z
**Commit de referência**: eb06901 (pre-commit hardened)
