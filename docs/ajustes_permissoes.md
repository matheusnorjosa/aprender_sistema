# Plano de Ajustes de Permissões - Django AS 2025

**Data:** 2025-08-22  
**Objetivo:** Corrigir gaps de permissões identificados na auditoria para alinhar 100% com responsabilidades das planilhas

## 1. RESUMO DO PLANO

### 1.1 Prioridade e Cronograma
- **🔴 Fase 1 (URGENTE)**: 3 ajustes críticos - implementar em 1-2 dias
- **🟡 Fase 2 (IMPORTANTE)**: 8 ajustes importantes - implementar em 1 semana  
- **🔵 Fase 3 (MELHORIAS)**: 7 ajustes de melhorias - implementar em 2-4 semanas

### 1.2 Impacto Esperado
- Restaurar **100% das capacidades operacionais** perdidas na migração
- Reduzir dependência de admin para tarefas rotineiras
- Permitir autogestão de formadores
- Melhorar eficiência operacional

## 2. FASE 1 - AJUSTES URGENTES (1-2 dias)

### 2.1 🔴 CRÍTICO: Restaurar sync_calendar para controle
**Problema**: Grupo controle perdeu capacidade de sincronizar Google Calendar

```python
# core/management/commands/fix_urgent_permissions.py
def fix_controle_sync_calendar():
    controle_group = Group.objects.get(name='controle')
    sync_perm = Permission.objects.get(
        content_type__app_label='core',
        codename='sync_calendar'
    )
    controle_group.permissions.add(sync_perm)
```

**Teste**: Verificar se usuário controle consegue acessar `/calendario/sync/`

### 2.2 🔴 CRÍTICO: Formações para coordenadores
**Problema**: Coordenadores não conseguem criar/editar formações (responsabilidade original das planilhas)

```python
# Adicionar permissões ao grupo coordenador
def fix_coordenador_formacoes():
    coordenador_group = Group.objects.get(name='coordenador')
    formacao_perms = Permission.objects.filter(
        content_type__app_label='planilhas',
        codename__in=['add_formacao', 'change_formacao', 'view_formacao']
    )
    coordenador_group.permissions.add(*formacao_perms)
```

**Teste**: Coordenador deve acessar `/planilhas/formacoes/add/`

### 2.3 🔴 CRÍTICO: Disponibilidade para formadores
**Problema**: Formadores não conseguem gerenciar própria disponibilidade

```python
# Adicionar permissões ao grupo formador
def fix_formador_disponibilidade():
    formador_group = Group.objects.get(name='formador')
    disp_perms = Permission.objects.filter(
        content_type__app_label='core',
        codename__in=['add_disponibilidadeformadores', 'change_disponibilidadeformadores']
    )
    formador_group.permissions.add(*disp_perms)
```

**Teste**: Formador deve acessar `/disponibilidade/minha/`

## 3. FASE 2 - AJUSTES IMPORTANTES (1 semana)

### 3.1 🟡 Dados mestres para controle
**Problema**: Controle não consegue gerenciar formadores, municípios e projetos

```python
def fix_controle_dados_mestres():
    controle_group = Group.objects.get(name='controle')
    
    # Formadores
    formador_perms = Permission.objects.filter(
        content_type__app_label='core',
        codename__in=['add_formador', 'change_formador', 'view_formador']
    )
    
    # Municípios e Projetos
    municipio_perms = Permission.objects.filter(
        content_type__app_label='core',
        codename__in=['add_municipio', 'change_municipio']
    )
    projeto_perms = Permission.objects.filter(
        content_type__app_label='core',
        codename__in=['add_projeto', 'change_projeto']
    )
    
    controle_group.permissions.add(*formador_perms, *municipio_perms, *projeto_perms)
```

### 3.2 🟡 Deslocamentos para coordenadores
**Problema**: Coordenadores não conseguem controlar deslocamentos

```python
def fix_coordenador_deslocamentos():
    coordenador_group = Group.objects.get(name='coordenador')
    desl_perms = Permission.objects.filter(
        content_type__app_label='core',
        codename__in=['add_deslocamento', 'change_deslocamento', 'view_deslocamento']
    )
    coordenador_group.permissions.add(*desl_perms)
```

### 3.3 🟡 Permissão de importação para controle
**Problema**: Controle precisa importar dados mas não tem permissão específica

```python
# Criar permissão customizada
def create_import_permission():
    ct = ContentType.objects.get_for_model(LogAuditoria)
    import_perm, created = Permission.objects.get_or_create(
        codename='import_data',
        name='Can import data from external sources',
        content_type=ct
    )
    
    controle_group = Group.objects.get(name='controle')
    controle_group.permissions.add(import_perm)
```

### 3.4 🟡 Conectar formadores para controle
**Problema**: Apenas admin pode conectar formadores a usuários

```python
def fix_controle_connect_formadores():
    # Permitir que controle edite campo usuario do Formador
    # Isso requer mudança no admin.py ou criar view específica
    pass  # Implementar view customizada
```

### 3.5 🟡 View todas solicitações para coordenadores
**Problema**: Coordenadores só veem próprias solicitações, mas nas planilhas viam mais

```python
def fix_coordenador_view_all():
    coordenador_group = Group.objects.get(name='coordenador')
    all_solic_perm = Permission.objects.get(
        content_type__app_label='core',
        codename='view_all_solicitacoes'
    )
    coordenador_group.permissions.add(all_solic_perm)
```

## 4. FASE 3 - MELHORIAS (2-4 semanas)

### 4.1 🔵 Views específicas por formador
**Implementar**: Views filtradas automaticamente por formador logado

```python
# core/views.py
class FormadorEventListView(LoginRequiredMixin, PermissionRequiredMixin, ListView):
    permission_required = 'core.view_own_events'
    
    def get_queryset(self):
        if hasattr(self.request.user, 'formador_profile'):
            formador = self.request.user.formador_profile
            return Solicitacao.objects.filter(
                formadores=formador,
                status='Aprovado'
            )
        return Solicitacao.objects.none()
```

### 4.2 🔵 Dashboard para diretoria
**Implementar**: Dashboard executivo com métricas consolidadas

```python
# core/views.py  
class DiretoriaDashboardView(LoginRequiredMixin, PermissionRequiredMixin, TemplateView):
    permission_required = 'core.view_relatorios'
    template_name = 'core/dashboard_diretoria.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update({
            'total_eventos_mes': Solicitacao.objects.filter(/* filtros */),
            'formadores_ativos': Formador.objects.filter(ativo=True).count(),
            # ... outras métricas
        })
        return context
```

### 4.3 🔵 Sistema de notificações
**Implementar**: Notificações básicas por email/dashboard

```python
# core/notifications.py
from django.core.mail import send_mail
from django.contrib.auth.models import Group

def notify_status_change(solicitacao, old_status, new_status):
    if new_status == 'Aprovado':
        # Notificar coordenador
        coordenadores = Group.objects.get(name='coordenador').user_set.all()
        for coord in coordenadores:
            send_mail(
                subject=f'Evento Aprovado: {solicitacao.titulo_evento}',
                message=f'O evento foi aprovado...',
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[coord.email]
            )
```

### 4.4 🔵 Validação robusta de dados
**Implementar**: Validações personalizadas nos models/forms

```python
# core/models.py - adicionar ao Solicitacao
def clean(self):
    super().clean()
    if self.data_inicio >= self.data_fim:
        raise ValidationError('Data início deve ser anterior à data fim')
    
    # Verificar conflito de formadores
    conflitos = DisponibilidadeFormadores.objects.filter(
        formador__in=self.formadores.all(),
        data_bloqueio=self.data_inicio.date(),
        hora_inicio__lte=self.data_inicio.time(),
        hora_fim__gte=self.data_fim.time()
    )
    if conflitos.exists():
        raise ValidationError('Conflito de disponibilidade detectado')
```

### 4.5 🔵 Backup automático
**Implementar**: Management command agendado

```python
# core/management/commands/backup_data.py
from django.core.management.base import BaseCommand
from django.core.management import call_command
import os
from datetime import datetime

class Command(BaseCommand):
    def handle(self, *args, **options):
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        backup_file = f'backup_{timestamp}.json'
        
        with open(backup_file, 'w') as f:
            call_command('dumpdata', stdout=f)
        
        # Upload para storage seguro
        # ... implementar upload
```

## 5. IMPLEMENTAÇÃO TÉCNICA

### 5.1 Script Unificado de Correção
**Arquivo**: `core/management/commands/fix_permissions_audit.py`

```python
from django.core.management.base import BaseCommand
from django.contrib.auth.models import Group, Permission
from django.contrib.contenttypes.models import ContentType

class Command(BaseCommand):
    help = 'Fix permissions based on audit findings'

    def add_arguments(self, parser):
        parser.add_argument('--phase', type=str, choices=['1', '2', '3', 'all'], 
                          default='all', help='Which phase to execute')

    def handle(self, *args, **options):
        phase = options['phase']
        
        if phase in ['1', 'all']:
            self.stdout.write('=== FASE 1: AJUSTES URGENTES ===')
            self.fix_controle_sync_calendar()
            self.fix_coordenador_formacoes()
            self.fix_formador_disponibilidade()
            
        if phase in ['2', 'all']:
            self.stdout.write('=== FASE 2: AJUSTES IMPORTANTES ===')
            self.fix_controle_dados_mestres()
            self.fix_coordenador_deslocamentos()
            self.create_import_permission()
            self.fix_coordenador_view_all()
            
        if phase in ['3', 'all']:
            self.stdout.write('=== FASE 3: MELHORIAS ===')
            self.create_custom_views()
            
        self.stdout.write(self.style.SUCCESS('✅ Correções aplicadas com sucesso!'))

    def fix_controle_sync_calendar(self):
        # ... implementação
        pass
        
    # ... outras funções
```

### 5.2 Execução
```bash
# Fase 1 - Urgente (executar imediatamente)
python manage.py fix_permissions_audit --phase=1

# Teste após Fase 1
python manage.py test core.tests_permissions

# Fase 2 - Importante (1 semana)
python manage.py fix_permissions_audit --phase=2

# Fase 3 - Melhorias (2-4 semanas)
python manage.py fix_permissions_audit --phase=3
```

### 5.3 Verificação Pós-Implementação
**Script de teste**: `test_permissions_after_fix.py`

```python
# Teste automatizado para validar todas as correções
def test_coordenador_permissions():
    coordenador = User.objects.filter(groups__name='coordenador').first()
    assert coordenador.has_perm('planilhas.add_formacao')
    assert coordenador.has_perm('core.add_deslocamento')
    # ... outros testes

def test_controle_permissions():
    controle = User.objects.filter(groups__name='controle').first()
    assert controle.has_perm('core.sync_calendar')
    assert controle.has_perm('core.add_formador')
    # ... outros testes

def test_formador_permissions():
    formador = User.objects.filter(groups__name='formador').first()
    assert formador.has_perm('core.add_disponibilidadeformadores')
    # ... outros testes
```

## 6. CRONOGRAMA DE IMPLEMENTAÇÃO

### Semana 1
- **Dia 1**: Implementar Fase 1 (ajustes urgentes)
- **Dia 2**: Testar e validar Fase 1
- **Dia 3-5**: Implementar Fase 2 (ajustes importantes)

### Semana 2-3  
- **Semana 2**: Testar e validar Fase 2
- **Semana 3**: Começar Fase 3 (views específicas, dashboard)

### Semana 4-6
- **Semana 4**: Sistema de notificações
- **Semana 5**: Backup automático e validações
- **Semana 6**: Teste final e documentação

## 7. RISCOS E CONTINGÊNCIAS

### 7.1 Riscos de Implementação
- **Quebra de funcionalidade existente**: Fazer backup antes de cada fase
- **Conflito de permissões**: Testar cada ajuste isoladamente  
- **Impacto em produção**: Implementar primeiro em ambiente de desenvolvimento

### 7.2 Plano de Rollback
```bash
# Backup pré-implementação
python manage.py dumpdata auth.Group auth.User > backup_permissions.json

# Rollback se necessário  
python manage.py flush
python manage.py loaddata backup_permissions.json
```

## 8. MÉTRICAS DE SUCESSO

### 8.1 KPIs Pós-Implementação
- **100% das responsabilidades das planilhas** funcionando no Django
- **0 gaps críticos** na matriz de responsabilidades
- **Redução de 50%** na dependência de admin para tarefas rotineiras
- **90% de satisfação** dos usuários com nova funcionalidade

### 8.2 Teste de Aceitação
Cada perfil deve conseguir executar todas as suas responsabilidades originais das planilhas através do Django AS.

---

**STATUS**: 🔄 **Pronto para implementação**  
**PRÓXIMO PASSO**: Executar `python manage.py fix_permissions_audit --phase=1`

**RESPONSÁVEL**: Desenvolvedores Django AS  
**PRAZO**: Fase 1 em 2 dias, demais fases conforme cronograma