# GRUPOS ORGANIZACIONAIS - APRENDER SISTEMA
## 13 Grupos Implementados - 26/08/2025

---

## 📊 **ESTRUTURA HIERÁRQUICA COMPLETA**

### **🔴 NÍVEL TÉCNICO/ADMINISTRATIVO (26 permissões)**
- **`admin`** - Administradores técnicos do sistema
- **`dat`** - Desenvolvimento e Apoio Tecnológico (setor DAT)

**Permissões:** Acesso completo + criação de usuários + todas as funcionalidades

### **🟡 NÍVEL COORDENAÇÃO (3 permissões)**  
- **`coordenador`** - Coordenadores regionais
- **`apoio_coordenacao`** - Apoio de Coordenação (auxilia coordenadores)

**Permissões:** Solicitar eventos, visualizar eventos, meus eventos

### **🟠 NÍVEL SUPERVISÃO (5 permissões)**
- **`superintendencia`** - Supervisão/aprovação de eventos  
- **`gerente_aprender`** - Gerente do Programa Aprender

**Permissões:** Aprovar eventos, visualizar logs, gerenciar aprovações

### **🔵 OUTROS NÍVEIS OPERACIONAIS**
- **`controle`** (13 permissões) - Controle operacional + API + Google Calendar
- **`formador`** (3 permissões) - Formadores/instrutores + bloqueio de agenda  
- **`diretoria`** (5 permissões) - Visão estratégica + relatórios consolidados

### **⚪ GRUPOS FUTUROS (1 permissão cada)**
- **`logistica`** - Setor de Logística  
- **`comercial`** - Setor Comercial
- **`financeiro`** - Setor Financeiro
- **`rh`** - Recursos Humanos

**Permissões:** Visibilidade básica (view_solicitacao) para futuras funcionalidades

---

## 🎯 **RESUMO POR FUNCIONALIDADE**

### **CRIAR USUÁRIOS:**
- ✅ `admin`, `dat`

### **SOLICITAR EVENTOS:**  
- ✅ `coordenador`, `apoio_coordenacao`

### **APROVAR EVENTOS:**
- ✅ `superintendencia`, `gerente_aprender`

### **FORMAR/ENSINAR:**
- ✅ `formador` (+ bloqueio de agenda)

### **CONTROLE OPERACIONAL:**
- ✅ `controle` (+ API, Google Calendar, municípios, compras)

### **VISÃO EXECUTIVA:**
- ✅ `diretoria` (+ relatórios, dashboards)

### **VISIBILIDADE BÁSICA:**
- ✅ `logistica`, `comercial`, `financeiro`, `rh`

---

## 📱 **VISIBILIDADE NO MENU**

### **Admin/DAT veem TUDO:**
- Todas as seções (Coordenação, Formador, Superintendência, Controle, Diretoria, Sistema)

### **Coordenador/Apoio Coordenação veem:**
- Seção "Coordenação" (Solicitar Evento, Meus Eventos)

### **Superintendência/Gerente Aprender veem:**
- Seção "Superintendência" (Aprovações, Deslocamentos, Cadastros)

### **Controle vê:**
- Seção "Controle" (Monitor GC, APIs, Formações, Compras)

### **Formador vê:**
- Seção "Formador" (Meus Eventos, Bloqueios)

### **Diretoria vê:**
- Seção "Diretoria" (Dashboards, Relatórios, Métricas)

### **Grupos Futuros veem:**
- Apenas "Principal" (Início, Mapa Mensal)

---

## ⚙️ **COMANDOS DE GESTÃO**

### **Recriar todos os grupos:**
```bash
python manage.py setup_groups
```

### **Verificar grupos existentes:**
```bash  
python manage.py shell -c "from django.contrib.auth.models import Group; [print(f'{g.name}: {g.permissions.count()}') for g in Group.objects.all()]"
```

### **Atribuir usuário a grupo (via shell):**
```python
from core.models import Usuario
from django.contrib.auth.models import Group

user = Usuario.objects.get(username='nome_usuario')  
group = Group.objects.get(name='dat')
user.groups.add(group)
```

### **Criar usuário via interface:**
- Admin/DAT podem usar: `/usuarios/novo/`
- Selecionar grupos na criação

---

## 🚀 **EXPANSÃO FUTURA**

### **Para ativar um setor futuro:**
1. **Adicionar permissões específicas** ao grupo em `setup_groups.py`
2. **Criar views/URLs** específicas do setor  
3. **Adicionar seção no menu** base.html
4. **Re-executar** `python manage.py setup_groups`

### **Exemplo - ativar Logística:**
```python
'logistica': [
    'view_solicitacao',
    'view_produto',      # Ver produtos
    'view_compra',       # Ver compras  
    'add_entrega',       # Registrar entregas (futuro)
    'view_estoque',      # Ver estoque (futuro)
]
```

---

## ✅ **STATUS ATUAL**

- **13 grupos criados** ✅
- **Hierarquia organizacional** refletida ✅  
- **Permissões por nível** funcionais ✅
- **Menu lateral** adaptativo ✅
- **Base sólida** para expansão ✅

**Sistema pronto para toda a estrutura organizacional da empresa!** 🎯

---

**Data:** 26/08/2025  
**Implementado por:** Claude Code  
**Status:** ✅ **CONCLUÍDO**