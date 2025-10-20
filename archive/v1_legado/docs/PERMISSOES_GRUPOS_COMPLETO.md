# 🔐 PERMISSÕES E GRUPOS COMPLETO - SISTEMA APRENDER

**Versão**: 2.0.0 Unificada
**Data**: 30 de Setembro de 2025
**Status**: ✅ Sistema de Permissões Consolidado

---

## 📑 ÍNDICE

1. [Resumo Executivo](#resumo-executivo)
2. [Grupos Organizacionais](#grupos-organizacionais)
3. [Hierarquia Organizacional](#hierarquia-organizacional)
4. [Migração do Sistema de Permissões](#migração-do-sistema-de-permissões)
5. [Estrutura de Setores](#estrutura-de-setores)
6. [Fluxo de Aprovação](#fluxo-de-aprovação)
7. [Matriz de Permissões](#matriz-de-permissões)

---

## 🎯 RESUMO EXECUTIVO

Este documento consolida todo o sistema de permissões e grupos do Sistema Aprender, incluindo a estrutura organizacional, hierarquia, migração de permissões e fluxos de aprovação.

### Status Geral: ✅ **SISTEMA DE PERMISSÕES COMPLETO**

### Principais Características:
- ✅ **13 grupos organizacionais** implementados
- ✅ **Sistema nativo Django** com Groups e Permissions
- ✅ **Hierarquia organizacional** bem definida
- ✅ **Fluxo de aprovação** hierárquico
- ✅ **Migração completa** do sistema antigo

---

## 👥 GRUPOS ORGANIZACIONAIS

### Estrutura Hierárquica Completa

#### 🔴 Nível Técnico/Administrativo (26 permissões)
- **`admin`** - Administradores técnicos do sistema
- **`dat`** - Desenvolvimento e Apoio Tecnológico (setor DAT)

**Permissões:** Acesso completo + criação de usuários + todas as funcionalidades

#### 🟡 Nível Coordenação (3 permissões)
- **`coordenador`** - Coordenadores regionais
- **`apoio_coordenacao`** - Apoio de Coordenação (auxilia coordenadores)

**Permissões:** Solicitar eventos, visualizar eventos, meus eventos

#### 🟠 Nível Supervisão (5 permissões)
- **`superintendencia`** - Supervisão/aprovação de eventos
- **`gerente_aprender`** - Gerente do Programa Aprender

**Permissões:** Aprovar eventos, visualizar logs, gerenciar aprovações

#### 🔵 Outros Níveis Operacionais
- **`controle`** (13 permissões) - Controle operacional + API + Google Calendar
- **`formador`** (3 permissões) - Formadores/instrutores + bloqueio de agenda
- **`diretoria`** (5 permissões) - Visão estratégica + relatórios consolidados

#### 🟢 Níveis de Apoio
- **`rh`** (2 permissões) - Recursos Humanos
- **`logistica`** (2 permissões) - Logística
- **`financeiro`** (2 permissões) - Financeiro
- **`editorial`** (2 permissões) - Editorial

### Distribuição de Usuários por Grupo
- **coordenador**: 37 usuários
- **formador**: 73 usuários
- **superintendencia**: 10 usuários
- **controle**: 1 usuário
- **diretoria**: 1 usuário
- **admin**: 1 usuário

---

## 🏢 HIERARQUIA ORGANIZACIONAL

### Modelo de Setores
O sistema utiliza o modelo `Setor` para representar a estrutura organizacional:

```python
class Setor(models.Model):
    nome = CharField(max_length=100, unique=True)
    sigla = CharField(max_length=20, unique=True)
    vinculado_superintendencia = BooleanField(default=False)
    ativo = BooleanField(default=True)
```

**Campos principais:**
- `vinculado_superintendencia`: Define se projetos do setor requerem aprovação
- `sigla`: Abreviação para identificação (ex: SUPER, VIDAS, LOC)

### Setores Cadastrados

#### Superintendência (vinculado_superintendencia=True)
- **Sigla**: SUPER
- **Característica**: Projetos requerem aprovação da superintendência
- **Projetos**: AMMA, CATAVENTOS, CIRANDAR, ESCREVER COMUNICAR E SER, Lendo e Escrevendo, MIUDEZAS, Novo Lendo, TEMA, TRÂNSITO LEGAL (todos), UNI DUNI TÊ

#### Setores Não-Superintendência (vinculado_superintendencia=False)
1. **Vidas** (VIDAS) - Vida e Matemática, Vida e Ciências, Vida e Linguagem
2. **ACerta** (ACERTA) - ACerta Matemática, ACerta Língua Portuguesa
3. **Brincando e Aprendendo** (BRINC) - Brincando e Aprendendo
4. **Outros** (OUTROS) - Projetos diversos

### Estrutura Hierárquica
```
🏢 SISTEMA APRENDER
├── 🔴 Nível Técnico/Administrativo
│   ├── admin (Administradores)
│   └── dat (Desenvolvimento e Apoio Tecnológico)
├── 🟠 Nível Supervisão
│   ├── superintendencia (Supervisão)
│   └── gerente_aprender (Gerente do Programa)
├── 🟡 Nível Coordenação
│   ├── coordenador (Coordenadores)
│   └── apoio_coordenacao (Apoio de Coordenação)
├── 🔵 Nível Operacional
│   ├── controle (Controle Operacional)
│   ├── formador (Formadores)
│   └── diretoria (Diretoria)
└── 🟢 Nível de Apoio
    ├── rh (Recursos Humanos)
    ├── logistica (Logística)
    ├── financeiro (Financeiro)
    └── editorial (Editorial)
```

---

## 🔄 MIGRAÇÃO DO SISTEMA DE PERMISSÕES

### Resumo da Implementação
Este documento detalha a migração do sistema de autorização baseado no campo `papel` para o sistema nativo do Django usando Groups e Permissions.

### Status da Migração
✅ **CONCLUÍDA** - Sistema totalmente implementado e testado

### Fases Implementadas
1. **✅ FASE 1**: Análise do uso atual do campo `papel`
2. **✅ FASE 2**: Criação do sistema de Groups e Permissions
3. **✅ FASE 3**: Criação de permissões customizadas
4. **✅ FASE 4**: Atualização de views e mixins
5. **✅ FASE 5**: Conexão do modelo Formador ao Usuario
6. **✅ FASE 6**: Testes completos do sistema
7. **✅ FASE 7**: Documentação e compatibilidade

### Arquitetura Implementada

#### Django Groups Criados
| Grupo | Permissões | Descrição |
|-------|------------|-----------|
| `coordenador` | 5 permissões | Criação e gestão de solicitações |
| `superintendencia` | 10 permissões | Aprovação de eventos + coordenação |
| `controle` | 5 permissões | Monitoramento e auditoria |
| `formador` | 1 permissão | Visualização de próprios eventos |
| `diretoria` | 5 permissões | Relatórios e visão estratégica |
| `admin` | Todas | Administração completa |

#### Permissões Customizadas Criadas
- `sync_calendar` - Sincronização com Google Calendar
- `view_relatorios` - Visualização de relatórios
- `add_eventogooglecalendar` - Criação de eventos no Google Calendar
- `change_eventogooglecalendar` - Edição de eventos no Google Calendar

### Comando de Migração
```bash
python manage.py setup_groups
```

**Funcionalidades:**
- Cria todos os grupos necessários
- Atribui permissões apropriadas
- Mantém compatibilidade com sistema antigo
- Logs detalhados da migração

---

## 🏗️ ESTRUTURA DE SETORES

### Modelo de Setores Implementado
```python
class Setor(models.Model):
    nome = models.CharField(max_length=100, unique=True)
    sigla = models.CharField(max_length=20, unique=True)
    vinculado_superintendencia = models.BooleanField(default=False)
    ativo = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "Setor"
        verbose_name_plural = "Setores"
        ordering = ['nome']
    
    def __str__(self):
        return f"{self.nome} ({self.sigla})"
```

### Setores Cadastrados no Sistema

#### 1. Superintendência (SUPER)
- **vinculado_superintendencia**: True
- **Projetos vinculados**: 9 projetos
- **Característica**: Requer aprovação da superintendência

#### 2. Vidas (VIDAS)
- **vinculado_superintendencia**: False
- **Projetos vinculados**: 3 projetos
- **Característica**: Aprovação direta

#### 3. ACerta (ACERTA)
- **vinculado_superintendencia**: False
- **Projetos vinculados**: 2 projetos
- **Característica**: Aprovação direta

#### 4. Brincando e Aprendendo (BRINC)
- **vinculado_superintendencia**: False
- **Projetos vinculados**: 1 projeto
- **Característica**: Aprovação direta

#### 5. Outros (OUTROS)
- **vinculado_superintendencia**: False
- **Projetos vinculados**: Projetos diversos
- **Característica**: Aprovação direta

### Lógica de Aprovação por Setor
```python
def requires_superintendence_approval(projeto):
    """Verifica se projeto requer aprovação da superintendência"""
    return projeto.setor.vinculado_superintendencia
```

---

## 🔄 FLUXO DE APROVAÇÃO

### Fluxo Principal
1. **Coordenador** cria solicitação → Status: PENDENTE
2. **Superintendência** aprova/reprova → Status: APROVADO/REPROVADO
3. **Controle** agenda no Google Calendar → Status: PRE_AGENDA
4. **Formador** executa evento → Status: REALIZADO

### Fluxo por Setor

#### Setores com Superintendência (vinculado_superintendencia=True)
```
Coordenador → Superintendência → Controle → Formador
     ↓              ↓              ↓          ↓
  PENDENTE      APROVADO      PRE_AGENDA   REALIZADO
```

#### Setores sem Superintendência (vinculado_superintendencia=False)
```
Coordenador → Controle → Formador
     ↓           ↓          ↓
  PENDENTE   PRE_AGENDA   REALIZADO
```

### Estados de Solicitação
- **PENDENTE**: Aguardando aprovação
- **APROVADO**: Aprovado pela superintendência
- **REPROVADO**: Reprovado pela superintendência
- **PRE_AGENDA**: Agendado no Google Calendar
- **REALIZADO**: Evento realizado
- **CANCELADO**: Evento cancelado

---

## 📊 MATRIZ DE PERMISSÕES

### Permissões por Grupo

#### Admin (Todas as permissões)
- ✅ Acesso completo ao sistema
- ✅ Criação de usuários
- ✅ Gestão de grupos
- ✅ Configurações do sistema

#### Coordenador (5 permissões)
- ✅ `add_solicitacao` - Criar solicitações
- ✅ `change_solicitacao` - Editar próprias solicitações
- ✅ `view_solicitacao` - Visualizar solicitações
- ✅ `view_eventogooglecalendar` - Visualizar eventos
- ✅ `view_disponibilidadeformadores` - Visualizar disponibilidade

#### Superintendência (10 permissões)
- ✅ Todas as permissões de coordenador
- ✅ `change_aprovacao` - Aprovar/reprovar solicitações
- ✅ `view_aprovacao` - Visualizar aprovações
- ✅ `view_logauditoria` - Visualizar logs
- ✅ `view_relatorios` - Visualizar relatórios

#### Controle (13 permissões)
- ✅ Todas as permissões de superintendência
- ✅ `sync_calendar` - Sincronizar com Google Calendar
- ✅ `add_eventogooglecalendar` - Criar eventos no Google Calendar
- ✅ `change_eventogooglecalendar` - Editar eventos no Google Calendar
- ✅ `view_compra` - Visualizar compras
- ✅ `add_compra` - Criar compras
- ✅ `change_compra` - Editar compras

#### Formador (3 permissões)
- ✅ `view_solicitacao` - Visualizar próprias solicitações
- ✅ `view_disponibilidadeformadores` - Visualizar disponibilidade
- ✅ `add_disponibilidadeformadores` - Bloquear agenda

#### Diretoria (5 permissões)
- ✅ `view_relatorios` - Visualizar relatórios
- ✅ `view_solicitacao` - Visualizar todas as solicitações
- ✅ `view_aprovacao` - Visualizar aprovações
- ✅ `view_logauditoria` - Visualizar logs
- ✅ `view_eventogooglecalendar` - Visualizar eventos

### Permissões Customizadas
- **`sync_calendar`**: Sincronização com Google Calendar
- **`view_relatorios`**: Visualização de relatórios
- **`add_eventogooglecalendar`**: Criação de eventos no Google Calendar
- **`change_eventogooglecalendar`**: Edição de eventos no Google Calendar

---

## 📝 CHANGELOG

### Versão 2.0.0 Unificada (30/09/2025)
- ✅ Unificação de 3 documentos de permissões
- ✅ Consolidação do sistema de grupos
- ✅ Hierarquia organizacional integrada
- ✅ Fluxo de aprovação documentado

### Versão 1.0.0 (26/08/2025)
- ✅ Sistema de permissões implementado
- ✅ Grupos organizacionais criados
- ✅ Migração concluída

---

**🔐 PERMISSÕES E GRUPOS COMPLETO - SISTEMA APRENDER**

*Documento unificado em: 2025-09-30*
*Status: ✅ SISTEMA DE PERMISSÕES CONSOLIDADO*
