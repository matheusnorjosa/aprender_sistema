# Migração do Sistema de Permissões

## Resumo da Implementação

Este documento detalha a migração do sistema de autorização baseado no campo `papel` para o sistema nativo do Django usando Groups e Permissions.

## Status da Migração

✅ **CONCLUÍDA** - Sistema totalmente implementado e testado

### Fases Implementadas

1. **✅ FASE 1**: Análise do uso atual do campo `papel`
2. **✅ FASE 2**: Criação do sistema de Groups e Permissions  
3. **✅ FASE 3**: Criação de permissões customizadas
4. **✅ FASE 4**: Atualização de views e mixins
5. **✅ FASE 5**: Conexão do modelo Formador ao Usuario
6. **✅ FASE 6**: Testes completos do sistema
7. **✅ FASE 7**: Documentação e compatibilidade

## Arquitetura Implementada

### 1. Django Groups Criados

| Grupo | Permissões | Descrição |
|-------|------------|-----------|
| `coordenador` | 5 permissões | Criação e gestão de solicitações |
| `superintendencia` | 10 permissões | Aprovação de eventos + coordenação |
| `controle` | 5 permissões | Monitoramento e auditoria |
| `formador` | 1 permissão | Visualização de próprios eventos |
| `diretoria` | 6 permissões | Visão estratégica e relatórios |
| `admin` | 15 permissões | Acesso total ao sistema |

### 2. Permissões Customizadas

```python
# Permissões adicionadas aos modelos
'core.sync_calendar'           # Sincronização com Google Calendar
'core.view_own_solicitacoes'   # Ver próprias solicitações
'core.view_all_solicitacoes'   # Ver todas as solicitações  
'core.view_calendar'           # Visualizar calendário
'core.view_relatorios'         # Acessar relatórios
'core.view_own_events'         # Ver próprios eventos (formador)
```

### 3. Novos Mixins Baseados em Groups

```python
# core/mixins.py
from core.mixins import (
    IsCoordenadorMixin,           # Baseado em grupo 'coordenador'
    IsSuperintendenciaMixin,      # Baseado em grupo 'superintendencia'
    IsFormadorMixin,              # Baseado em grupo 'formador'
    CanViewCalendarMixin,         # Baseado em permissão
    CanCreateSolicitacaoMixin,    # Baseado em permissão
    # ... outros mixins
)
```

### 4. Conexão Formador ↔ Usuario

```python
class Formador(models.Model):
    # ... campos existentes ...
    usuario = models.OneToOneField(
        Usuario, 
        on_delete=models.SET_NULL,
        related_name='formador_profile',
        null=True, blank=True
    )
    
    @property
    def has_formador_role(self):
        """Verifica se usuário conectado tem role formador"""
        if self.usuario:
            return self.usuario.groups.filter(name='formador').exists()
        return False
```

## Migrações Aplicadas

### 0009_setup_groups_permissions.py
- Criação dos 6 grupos principais
- Configuração inicial das permissões
- Sincronização inicial de usuários existentes

### 0010_add_custom_permissions.py  
- Adição de permissões customizadas aos modelos
- Atualização das Meta classes dos models

### 0011_assign_permissions_to_groups.py
- Atribuição correta de permissões aos grupos
- Re-sincronização de usuários existentes

### 0012_add_usuario_to_formador.py
- Adição do campo `usuario` ao modelo Formador
- Criação da relação OneToOne com Usuario

## Sistema de Sincronização Automática

### Signal de Sincronização

```python
# core/signals.py
@receiver(post_save, sender=Usuario)
def sync_user_role_to_group(sender, instance, created, **kwargs):
    """
    Sincroniza automaticamente o campo 'papel' com grupos Django
    Executado sempre que um usuário é salvo
    """
```

**Funcionamento:**
1. Usuário é criado/editado com campo `papel`
2. Signal automaticamente adiciona ao grupo correspondente
3. Remove de outros grupos de papel para evitar conflitos
4. Mantém outros grupos não relacionados a papéis

### Funções Utilitárias

```python
# Verificar se usuário tem papel específico
user_has_role(user, 'coordenador')  # True/False

# Verificar se usuário tem qualquer um dos papéis
user_has_any_role(user, ['coordenador', 'admin'])  # True/False

# Obter todos os papéis do usuário
get_user_role_names(user)  # ['coordenador']
```

## Compatibilidade Retroativa

### Período de Transição

Durante a implementação, o sistema mantém **dupla compatibilidade**:

1. **Campo `papel` mantido**: Continua existindo e funcionando
2. **Groups sincronizados**: Automaticamente via signals
3. **Mixins legados**: Disponíveis como `LegacyIsCoordenadorMixin`

### Views Atualizadas

```python
# Antes (baseado em papel)
class SolicitacaoCreateView(LoginRequiredMixin, IsCoordenadorMixin, CreateView):
    pass

# Depois (baseado em permissão)  
class SolicitacaoCreateView(LoginRequiredMixin, PermissionRequiredMixin, CreateView):
    permission_required = 'core.add_solicitacao'
```

### Templates Atualizados

```html
<!-- Antes -->
{% if user.papel == 'coordenador' %}

<!-- Depois -->
{% if perms.core.add_solicitacao %}
```

## Testes Implementados

### Script de Validação
- `test_permission_system.py`: Teste completo do sistema
- Verifica grupos, permissões, sincronização e funcionalidades

### Testes Unitários
- `core/tests_permissions.py`: Testes abrangentes
- Cobertura de migração, grupos, permissões e views

## Como Usar o Novo Sistema

### 1. Verificar Permissões em Views

```python
# Recomendado: usar PermissionRequiredMixin
class MinhaView(LoginRequiredMixin, PermissionRequiredMixin, View):
    permission_required = 'core.view_calendar'

# Alternativa: usar GroupRequiredMixin  
class MinhaView(LoginRequiredMixin, CanViewCalendarMixin, View):
    pass
```

### 2. Verificar Permissões em Templates

```html
<!-- Verificar permissão específica -->
{% if perms.core.add_solicitacao %}
    <a href="{% url 'core:solicitar_evento' %}">Solicitar Evento</a>
{% endif %}

<!-- Verificar múltiplas permissões -->
{% if perms.core.view_calendar and perms.core.view_relatorios %}
    <a href="{% url 'core:calendario' %}">Calendário</a>
{% endif %}
```

### 3. Verificar Permissões em Código

```python
# Em views, models, etc.
if request.user.has_perm('core.sync_calendar'):
    # executar sincronização
    pass

# Verificar múltiplas permissões
if request.user.has_perms(['core.add_solicitacao', 'core.view_calendar']):
    # ação que requer ambas permissões
    pass
```

## Próximos Passos (Futuras Melhorias)

### Fase 8 (Opcional): Remover Campo `papel`
Após período de estabilização, o campo `papel` pode ser removido:

1. **Verificar uso**: Garantir que não há código dependente
2. **Criar migração**: Remover campo e signal de sincronização  
3. **Limpar código**: Remover mixins legados e referências
4. **Atualizar testes**: Remover testes de compatibilidade

### Melhorias Futuras

1. **Permissões por objeto**: Implementar object-level permissions
2. **Audit trail**: Log automático de mudanças de permissões
3. **Interface admin**: Melhorar gestão de grupos/permissões no admin
4. **API permissions**: Implementar permissões para endpoints da API

## Benefícios Alcançados

✅ **Padronização**: Uso do sistema nativo do Django  
✅ **Flexibilidade**: Permissões granulares por funcionalidade  
✅ **Escalabilidade**: Fácil adição de novos papéis/permissões  
✅ **Manutenibilidade**: Código mais limpo e padrão  
✅ **Segurança**: Sistema mais robusto e auditável  
✅ **Compatibilidade**: Transição suave sem quebra  

## Comandos Úteis

```bash
# Verificar grupos existentes
python manage.py shell -c "from django.contrib.auth.models import Group; print([g.name for g in Group.objects.all()])"

# Verificar permissões de um grupo
python manage.py shell -c "from django.contrib.auth.models import Group; g = Group.objects.get(name='coordenador'); print([f'{p.content_type.app_label}.{p.codename}' for p in g.permissions.all()])"

# Executar teste completo
python test_permission_system.py

# Executar testes unitários de permissões
python manage.py test core.tests_permissions
```

---

**Status**: ✅ Implementação completa e testada  
**Data**: Janeiro 2025  
**Desenvolvido**: Sistema robusto baseado em Django Groups & Permissions