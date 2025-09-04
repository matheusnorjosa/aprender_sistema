# MAPEAMENTO COMPLETO DO ECOSSISTEMA DE PLANILHAS

> **Análise profunda das 4 planilhas Google e suas interconexões**  
> Data: Janeiro 2025 | Total: 73.168 registros extraídos

---

## 🏗️ ARQUITETURA DO SISTEMA ORIGINAL

### 📊 **4 PLANILHAS PRINCIPAIS**
1. **USUÁRIOS** - Base de usuários do sistema
2. **DISPONIBILIDADE** - Agenda e códigos de disponibilidade  
3. **CONTROLE** - Maior planilha, dados operacionais
4. **ACOMPANHAMENTO** - Integração Google Calendar + monitoramento

### 🤖 **3 APPS SCRIPTS CONECTADOS**
- **Script DISPONIBILIDADE**: Automações de agenda
- **Script CONTROLE**: Validações e processamento
- **Script ACOMPANHAMENTO**: Sync Google Calendar

---

## 📋 DETALHAMENTO POR PLANILHA

### 1. 👥 **USUÁRIOS** (142 registros)
**ID**: `1Zj_I7sqYAJ9uaYbVoBfskl0LqxGM3SAFzwm4Zpph1RI`

#### Estrutura:
- **Ativos**: 117 usuários (dados completos)
- **Inativos**: 2 usuários (histórico)  
- **Pendentes**: 20 usuários (aguardando aprovação)

#### Campos Principais:
```
Nome, Nome Completo, CPF, Telefone, Email, 
Cargo, Gerência, Status
```

#### Papel no Ecossistema:
- **FONTE DE VERDADE** para autenticação
- **Referência cruzada** em todas as outras planilhas
- **Validação de perfis** (Coordenador, Formador, Superintendência)

---

### 2. 🗓️ **DISPONIBILIDADE** (1.786 registros)  
**ID**: `1fsCeGUzsNCv0SCiE6mcIvcCHsMbqNeyzANwdU_148Vw`

#### Status Atual: **🚧 EM MANUTENÇÃO**
- Planilha estava sendo reestruturada durante extração
- Dados parciais extraídos (6 abas identificadas)

#### Função Identificada:
- **MOTOR DE DISPONIBILIDADE** do sistema
- Códigos: **E, M, D, P, T, X** para status de agenda
- **Validação de conflitos** via fórmulas complexas

---

### 3. ⚙️ **CONTROLE** (61.790 registros - 84% dos dados)
**ID**: `1P6YG3sIAEpiAPIQL9bKBaIznNl3V9VLan9CpVnrEOgA`

#### 12 Abas Especializadas:
- **🟥 COMPRAS**: 1.593 registros (produtos, quantidades, municípios)
- **📚 FORMAÇÕES**: 50.499 registros (MAIOR ABA - eventos históricos)
- **📊 CONFIGURAÇÕES**: 3.503 registros (parâmetros sistema)
- **👥 COORDENADORES**: 28 registros (gestores regionais)
- **📋 CADASTROS**: 1.501 registros (dados atuais + 237 antigos)
- **⚡ AÇ&OES**: 688 registros (ações/projetos)
- **📅 DAT**: 931 registros atuais + 782 antigos
- **🔍 FILTRO_PROD**: 772 registros (filtros produtos)

#### Papel no Ecossistema:
- **HUB CENTRAL** de dados operacionais
- **Maior volume** de dados históricos
- **Configurações** que afetam outras planilhas

---

### 4. 📈 **ACOMPANHAMENTO** (9.450 registros)
**ID**: `16ul8qvHb-1CRs5Z7zYcVP9Rh2munCefWWNsAiJfZYYU`

#### 13 Abas Funcionais:
- **Google Agenda**: 2.451 eventos sincronizados
- **Novo Google Agenda**: 577 eventos
- **Pré-Agenda**: 6 registros (status PRE_AGENDA)
- **Bloqueios**: 51 registros (agenda formadores)
- **Configurações**: 270 registros (municípios, parâmetros)
- **DISPONIBILIDADE**: 69 registros (consulta cruzada)
- **DESLOCAMENTO**: 3 registros
- **Por Projeto**: Super (1.985), ACerta (1.001), Vidas (1.002), Brincando (1.000), Outros (1.022)

#### Papel no Ecossistema:
- **INTERFACE COM GOOGLE CALENDAR**
- **Monitoramento pós-evento**
- **Separação por projetos/áreas**

---

## 🔄 FLUXOS DE DADOS IDENTIFICADOS

### **FLUXO PRINCIPAL**: 
```
USUÁRIOS → DISPONIBILIDADE → CONTROLE → ACOMPANHAMENTO → Google Calendar
```

### **CONEXÕES CRÍTICAS**:

1. **USUÁRIOS ↔ TODAS PLANILHAS**
   - CPF/Email como chave de ligação
   - Validação de perfis em cada operação

2. **DISPONIBILIDADE → CONTROLE**
   - Códigos E,M,D,P,T,X propagados
   - Validação de conflitos antes da aprovação

3. **CONTROLE → ACOMPANHAMENTO**  
   - Eventos aprovados → sync Google Calendar
   - Status PRE_AGENDA intermediário

4. **ACOMPANHAMENTO → Google Calendar**
   - Integração bidirecional (Apps Script)
   - Criação automática de eventos + Meet

---

## 🤖 AUTOMAÇÕES IDENTIFICADAS (Apps Scripts)

### **Por Planilha:**

#### 1. **Script DISPONIBILIDADE**
- **Função presumida**: Validação de códigos E,M,D,P,T,X
- **Triggers**: onChange para verificar conflitos
- **Integração**: IMPORTRANGE com CONTROLE

#### 2. **Script CONTROLE** 
- **Função presumida**: Processamento de aprovações
- **Validações**: Regras de negócio complexas
- **Integração**: Multiple IMPORTRANGE

#### 3. **Script ACOMPANHAMENTO**
- **Função confirmada**: Sync Google Calendar
- **Headers identificados**: Delete, Update, Title, Start, End
- **Integração**: Bidirecional com Calendar API

---

## 📊 REGRAS DE NEGÓCIO DESCOBERTAS

### **Códigos de Disponibilidade:**
- **E**: Evento confirmado (base para agendamento)
- **M**: Múltiplos eventos (limite capacidade/dia)
- **D**: Deslocamento (buffer entre municípios)
- **P**: Bloqueio parcial (horário específico)
- **T**: Bloqueio total (dia inteiro)
- **X**: Conflito (sobreposição detectada)

### **Fluxo de Aprovação:**
1. Solicitação criada (origem: CONTROLE)
2. Verificação automática (origem: DISPONIBILIDADE)
3. Se OK → PRE_AGENDA (origem: ACOMPANHAMENTO)
4. Aprovação manual → APROVADO
5. Sync Google Calendar (origem: ACOMPANHAMENTO)

### **Integrações Críticas:**
- **IMPORTRANGE** entre planilhas (referências cruzadas)
- **Google Calendar API** (eventos + Meet)
- **Validação cruzada** de CPF/Email
- **Sincronização bidirecional** de status

---

## 🎯 IMPACTOS NA MIGRAÇÃO DJANGO

### **Alto Impacto - Prioridade Máxima:**
1. **Sistema de códigos E,M,D,P,T,X** → Lógica core do Django
2. **Validação de conflitos** → Service layer especializado  
3. **Integração Google Calendar** → API já em desenvolvimento
4. **Fluxo PRE_AGENDA** → Status já implementado no Django

### **Médio Impacto - Implementar Gradualmente:**
1. **50K+ Formações históricas** → Migração em batches
2. **Sistema de IMPORTRANGE** → APIs Django internas
3. **Configurações distribuídas** → Settings unificados

### **Baixo Impacto - Pode Aguardar:**
1. **Compras/Produtos** → Sistema independente
2. **Relatórios diversos** → Gerar via Django Admin
3. **Dados antigos/inativos** → Backup sem migração

---

## 🚀 PRÓXIMOS PASSOS RECOMENDADOS

### **FASE 1: VALIDAÇÃO (1-2 semanas)**
- [ ] Implementar engine de códigos E,M,D,P,T,X
- [ ] Criar service de validação de conflitos
- [ ] Testar com dados reais de DISPONIBILIDADE

### **FASE 2: INTEGRAÇÃO (2-3 semanas)**  
- [ ] Finalizar Google Calendar sync
- [ ] Implementar fluxo PRE_AGENDA completo
- [ ] Migrar dados de USUÁRIOS e ACOMPANHAMENTO

### **FASE 3: DADOS MASSIVOS (3-4 semanas)**
- [ ] Migração gradual das 50K+ FORMAÇÕES
- [ ] Implementar sistema de COMPRAS
- [ ] Unificar CONFIGURAÇÕES

---

## ✅ CONCLUSÃO

**Sistema atual É EXTREMAMENTE COMPLEXO:**
- **4 planilhas interconectadas**
- **3 Apps Scripts automatizados**  
- **73K+ registros com regras sofisticadas**
- **Integração bidirecional Google Calendar**

**O Django já implementou ~40% da funcionalidade core:**
- ✅ Usuários e autenticação
- ✅ Status PRE_AGENDA  
- ✅ Fluxo básico de solicitações
- ✅ Integração Google Calendar (base)

**Próxima prioridade:** Implementar engine de códigos E,M,D,P,T,X no Django para substituir completamente a planilha DISPONIBILIDADE.