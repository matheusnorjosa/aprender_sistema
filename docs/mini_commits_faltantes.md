# 🚀 Plano de Mini-Commits para Gaps Restantes

**Base da Análise:** auditoria_impl_vs_planilhas.md  
**Prioridade:** Commits pequenos e focados para completar equivalência funcional

---

## 📋 **RESUMO EXECUTIVO**

**Status Atual:** AS é 95% funcionalmente equivalente às Planilhas Google  
**Gaps Identificados:** 4 interfaces CRUD faltantes para models já existentes  
**Esforço Estimado:** 3-4 commits pequenos (1-2 horas cada)  
**Criticidade:** Baixa - funcionalidades core já implementadas

---

## 🎯 **MINI-COMMITS PLANEJADOS**

### **Commit 1: Interface CRUD para Ações** 
**Prioridade:** ALTA  
**Esforço:** 2 horas  
**Arquivos afetados:** 3-4 arquivos

#### **Descrição:**
Implementar interface web completa para o modelo `Acao` (🟥 AÇÕES da planilha)

#### **Tarefas:**
- [ ] Criar `AcaoListView` com filtros por município, projeto, data
- [ ] Criar `AcaoCreateView` e `AcaoUpdateView` 
- [ ] Criar `AcaoDeleteView` com confirmação
- [ ] Template `acao_list.html` com tabela responsiva
- [ ] Template `acao_form.html` com campos:
  - Município, Projeto, Coordenador
  - Data entrega, Data carta, Data contato, Data reunião alinhamento
- [ ] URLs em `planilhas/urls.py`
- [ ] Adicionar link no menu lateral para grupo "controle"

#### **Testes:**
- [ ] `AcaoModelTestCase` - CRUD básico
- [ ] `AcaoViewTestCase` - Permissões e interface
- [ ] `AcaoFormTestCase` - Validação de campos

#### **Critério de Sucesso:**
✅ Usuário do grupo "controle" consegue gerenciar ações via interface web  
✅ Dados equivalentes à aba 🟥 AÇÕES da planilha

---

### **Commit 2: Interface CRUD para Dados DAT**
**Prioridade:** MÉDIA  
**Esforço:** 2 horas  
**Arquivos afetados:** 3-4 arquivos

#### **Descrição:**
Implementar interface web para o modelo `DadosDAT` (ℹ️ DAT da planilha)

#### **Tarefas:**
- [ ] Criar `DadosDATListView` com filtros
- [ ] Criar views de CRUD completo
- [ ] Templates com campos:
  - Município, Projeto
  - Aluno_qtde, Professor_qtde  
  - Status FORMAR/AVALIAR
- [ ] Estatísticas por projeto/município
- [ ] URLs e menu

#### **Testes:**
- [ ] `DadosDATModelTestCase`
- [ ] `DadosDATViewTestCase` 
- [ ] Teste de cálculos/estatísticas

#### **Critério de Sucesso:**
✅ Controle completo de dados alunos/turmas por município  
✅ Relatórios FORMAR/AVALIAR funcionais

---

### **Commit 3: Interface CRUD para Cadastros**
**Prioridade:** BAIXA  
**Esforço:** 1.5 horas  
**Arquivos afetados:** 3-4 arquivos

#### **Descrição:**
Implementar interface para `CadastroTipo` e `CadastroRegistro` (☑️ CADASTROS)

#### **Tarefas:**
- [ ] Views CRUD para `CadastroTipo`
- [ ] Views CRUD para `CadastroRegistro`
- [ ] Templates com relacionamento mestre-detalhe
- [ ] Filtros e busca
- [ ] URLs e menu

#### **Testes:**
- [ ] `CadastroTestCase` - CRUD completo
- [ ] Teste de relacionamentos

#### **Critério de Sucesso:**
✅ Gestão completa do sistema de cadastros  
✅ Controle FORMAR/AVALIAR por cadastro

---

### **Commit 4: Visão Anual de Disponibilidade**
**Prioridade:** BAIXA  
**Esforço:** 1 hora  
**Arquivos afetados:** 2 arquivos

#### **Descrição:**
Complementar sistema de disponibilidade com visão anual

#### **Tarefas:**
- [ ] Criar `DisponibilidadeAnualView`
- [ ] Template com calendário anual
- [ ] Estatísticas anuais por formador
- [ ] Integração com mapa mensal existente

#### **Testes:**
- [ ] `DisponibilidadeAnualTestCase`

#### **Critério de Sucesso:**
✅ Visão anual complementa mapa mensal existente  
✅ Equivalente à aba ANUAL da planilha Disponibilidade

---

## 📊 **MATRIZ DE DEPENDÊNCIAS E PRIORIDADES**

| Commit | Dependências | Impacto | Complexidade | Ordem Sugerida |
|--------|--------------|---------|--------------|----------------|
| **CRUD Ações** | Nenhuma | Alto | Baixa | 1º |
| **CRUD DAT** | Nenhuma | Médio | Baixa | 2º |
| **CRUD Cadastros** | Nenhuma | Baixo | Baixa | 3º |
| **Visão Anual** | Mapa mensal existente | Baixo | Baixa | 4º |

---

## 🔧 **IMPLEMENTAÇÃO RECOMENDADA**

### **Padrões a Seguir:**

1. **Views:** Usar mesmos padrões das Formações
   ```python
   class AcaoListView(LoginRequiredMixin, PermissionRequiredMixin, ListView):
       model = Acao
       permission_required = 'planilhas.view_acao'
   ```

2. **Templates:** Bootstrap + padrão existente
   ```html
   {% extends "core/base.html" %}
   <!-- Seguir estrutura de formacoes_list.html -->
   ```

3. **URLs:** Padrão RESTful
   ```python
   path('acoes/', views.AcaoListView.as_view(), name='acoes_list'),
   ```

4. **Testes:** Seguir estrutura existente em `planilhas/tests.py`

5. **Permissões:** Usar grupo "controle" existente

### **Checklist de Qualidade:**
- [ ] Responsivo (mobile-friendly)
- [ ] Filtros e busca funcionais  
- [ ] Validação de formulários
- [ ] Mensagens de sucesso/erro
- [ ] Testes com >80% cobertura
- [ ] Documentação em docstrings
- [ ] Permissões configuradas
- [ ] Menu atualizado

---

## 🎯 **RESULTADO FINAL ESPERADO**

Após implementação dos 4 commits:

| Métrica | Antes | Depois | Melhoria |
|---------|-------|--------|----------|
| **Cobertura Funcional** | 95% | 100% | +5% |
| **CRUDs Implementados** | 2/6 | 6/6 | +4 interfaces |
| **Equivalência Planilhas** | Parcial | Total | Completa |
| **Usabilidade** | Boa | Excelente | Interfaces faltantes |

### **Validação de Sucesso:**
✅ Usuário consegue replicar 100% do workflow das planilhas no AS  
✅ Todas as abas principais têm equivalente web funcional  
✅ Sistema de permissões controla acesso adequadamente  
✅ Performance mantida com novos CRUDs  
✅ Testes garantem qualidade das novas funcionalidades

---

## 📈 **ROADMAP PÓS-GAPS**

**Funcionalidades Opcionais (Não críticas):**

1. **Automações Avançadas:**
   - Relatórios periódicos automáticos
   - Notificações por email  
   - Export para Excel/PDF

2. **Integrações:**
   - API REST para integrações externas
   - Webhooks para sistemas terceiros

3. **Analytics:**
   - Dashboard avançado com métricas
   - Relatórios de uso do sistema

**Estimativa:** 2-3 sprints adicionais (opcional)

---

## ✅ **CONCLUSÃO**

O plano de mini-commits é **conservador e focado**, priorizando:
- ✅ Completar equivalência funcional 100%
- ✅ Manter qualidade e padrões existentes  
- ✅ Baixo risco de regressões
- ✅ Entrega incremental de valor

**Próxima ação recomendada:** Implementar Commit 1 (CRUD Ações)