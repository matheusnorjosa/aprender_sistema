# 🧪 GUIA DE TESTES FRONTEND - APRENDER SISTEMA v2

**Data**: 25/10/2025
**Frontend**: http://localhost:5173/
**Backend**: http://localhost:8002/
**Credenciais Admin**: admin / (senha configurada)

---

## ✅ PRÉ-REQUISITOS

- [x] Backend rodando em http://localhost:8002/ (Docker Compose)
- [x] Frontend rodando em http://localhost:5173/ (Vite)
- [x] Banco de dados com 2.235 registros importados
- [x] Usuário admin com todos os grupos

**Como fazer login**:
1. Acesse http://localhost:8002/admin/
2. Faça login com credenciais de admin
3. Depois acesse http://localhost:5173/

---

## 📋 CHECKLIST DE TESTES MANUAIS

### 1. 🏠 Página Inicial (/)

**URL**: http://localhost:5173/

- [ ] Carrega sem erros no console
- [ ] Exibe título "Aprender Sistema"
- [ ] Mostra links para navegação
- [ ] Links estão funcionando

---

### 2. 📝 Lista de Solicitações (/solicitacoes)

**URL**: http://localhost:5173/solicitacoes

**Dados esperados**: 1.957 solicitações (filtradas por fluxo SUPER se configurado)

**Testes**:
- [ ] Tabela carrega com dados
- [ ] Mostra colunas: Projeto, Município, Data Início, Data Fim, Status
- [ ] Filtro por status funciona (pendente/aprovado/reprovado)
- [ ] Filtro por fluxo funciona (SUPER/NAO_SUPER)
- [ ] Paginação funciona corretamente
- [ ] Busca funciona
- [ ] Dados aparecem formatados corretamente

**Verificar se dados aparecem**:
- [ ] Nomes de projetos aparecem (não "Município #89")
- [ ] Nomes de municípios aparecem
- [ ] Datas formatadas em PT-BR

---

### 3. ➕ Nova Solicitação (/solicitacoes/nova)

**URL**: http://localhost:5173/solicitacoes/nova

**Testes - Wizard Passo 1 (Dados Básicos)**:
- [ ] ComboBox "Projeto" carrega lista de 44 projetos
- [ ] ComboBox "Tipo de Evento" carrega 15 tipos
- [ ] ComboBox "Município" carrega 97 municípios
- [ ] PeoplePicker "Formadores" permite selecionar múltiplos
- [ ] Labels aparecem claramente (não campos sem rótulo)
- [ ] Placeholders aparecem nos campos
- [ ] Validação funciona (campos obrigatórios)

**Testes - Wizard Passo 2 (Datas e Horários)**:
- [ ] DatePicker funciona
- [ ] TimePicker funciona
- [ ] Validação de data/hora funciona

**Testes - Wizard Passo 3 (Revisão)**:
- [ ] Mostra resumo correto
- [ ] Botão "Enviar" funciona

**Testes - Fluxo SUPER**:
- [ ] Selecionar projeto "SMOKE SUPER" ou "Teste Auto SUPER"
- [ ] Preencher formulário completo
- [ ] Enviar solicitação
- [ ] **Verificar**: Solicitação criada com status="pendente"
- [ ] **Verificar**: Aparece em /aprovacoes

**Testes - Fluxo NAO_SUPER**:
- [ ] Selecionar qualquer outro projeto (ex: "ACerta")
- [ ] Preencher formulário completo
- [ ] Enviar solicitação
- [ ] **Verificar**: Solicitação criada com status="aprovado"
- [ ] **Verificar**: Aparece em /pre-agenda (não em /aprovacoes)

---

### 4. ✅ Aprovações (/aprovacoes)

**URL**: http://localhost:5173/aprovacoes

**Dados esperados**: Apenas solicitações com fluxo SUPER e status pendente (16 atualmente)

**Testes**:
- [ ] Tabela carrega com dados
- [ ] **Mostra apenas fluxo SUPER** (não NAO_SUPER)
- [ ] **Mostra apenas status pendente** (não aprovadas/reprovadas)
- [ ] Colunas aparecem corretamente
- [ ] Botões "Aprovar" e "Reprovar" aparecem apenas para usuários autorizados
- [ ] Botões **NÃO** aparecem para usuários sem permissão (PA-06)

**Teste de Aprovação**:
- [ ] Logar como admin (tem grupo Superintendência)
- [ ] Clicar em "Aprovar" em uma solicitação pendente
- [ ] **Verificar**: Status muda para "aprovado"
- [ ] **Verificar**: Solicitação desaparece de /aprovacoes
- [ ] **Verificar**: Solicitação aparece em /pre-agenda

**Teste de Reprovação**:
- [ ] Clicar em "Reprovar" em uma solicitação pendente
- [ ] Adicionar justificativa
- [ ] **Verificar**: Status muda para "reprovado"
- [ ] **Verificar**: Solicitação desaparece de /aprovacoes

---

### 5. 📅 Pré-Agenda (/pre-agenda)

**URL**: http://localhost:5173/pre-agenda

**Dados esperados**: Solicitações aprovadas (tanto SUPER quanto NAO_SUPER)

**Testes**:
- [ ] Tabela carrega com dados
- [ ] Mostra solicitações aprovadas de ambos os fluxos
- [ ] Colunas aparecem corretamente
- [ ] Botão "Preview GCal" funciona
- [ ] Botão "Publish" funciona (apenas para grupo Controle)
- [ ] Filtros funcionam

**Teste de Publicação (Google Calendar)**:
- [ ] Logar como usuário do grupo Controle
- [ ] Selecionar solicitação aprovada
- [ ] Clicar em "Preview GCal"
- [ ] **Verificar**: Mostra preview do evento
- [ ] Clicar em "Publish"
- [ ] **Verificar**: Status muda para publicado
- [ ] **Verificar**: Link do Meet é gerado (se feature ativa)

---

### 6. 🗺️ Mapa do Brasil (/mapa-brasil)

**URL**: http://localhost:5173/mapa-brasil

**Testes**:
- [ ] Mapa Leaflet carrega corretamente
- [ ] Marcadores aparecem nos estados
- [ ] Cores dos marcadores variam por quantidade de eventos
- [ ] Popup aparece ao clicar no marcador
- [ ] GeoJSON está renderizando corretamente
- [ ] Zoom funciona
- [ ] Pan funciona
- [ ] Legenda aparece

---

### 7. 📊 Dashboard de Controle

**URL**: http://localhost:5173/controle (se existir)

**Testes**:
- [ ] Gráficos carregam
- [ ] Dados estão corretos
- [ ] Filtros funcionam

---

### 8. 📊 Dashboard DAT

**URL**: http://localhost:5173/dat (se existir)

**Testes**:
- [ ] Gráficos carregam
- [ ] Dados estão corretos
- [ ] Filtros funcionam

---

## 🔍 TESTES DE INTEGRAÇÃO

### Fluxo Completo SUPER

1. **Criar Solicitação** (Coordenador):
   - [ ] Acessar /solicitacoes/nova
   - [ ] Selecionar projeto SUPER (ex: "SMOKE SUPER")
   - [ ] Preencher dados completos
   - [ ] Enviar
   - [ ] **Resultado**: Status = pendente

2. **Aprovar Solicitação** (Superintendência):
   - [ ] Acessar /aprovacoes
   - [ ] Ver a solicitação criada
   - [ ] Clicar "Aprovar"
   - [ ] **Resultado**: Status = aprovado

3. **Publicar no Google Calendar** (Controle):
   - [ ] Acessar /pre-agenda
   - [ ] Ver a solicitação aprovada
   - [ ] Clicar "Publish"
   - [ ] **Resultado**: Evento criado no Google Calendar

### Fluxo Completo NAO_SUPER

1. **Criar Solicitação** (Coordenador):
   - [ ] Acessar /solicitacoes/nova
   - [ ] Selecionar projeto NAO_SUPER (ex: "ACerta")
   - [ ] Preencher dados completos
   - [ ] Enviar
   - [ ] **Resultado**: Status = aprovado (auto-aprovado!)

2. **Verificar que NÃO aparece em /aprovacoes**:
   - [ ] Acessar /aprovacoes
   - [ ] **Verificar**: Solicitação NAO_SUPER não aparece

3. **Publicar no Google Calendar** (Controle):
   - [ ] Acessar /pre-agenda
   - [ ] Ver a solicitação (já aprovada)
   - [ ] Clicar "Publish"
   - [ ] **Resultado**: Evento criado no Google Calendar

---

## 🐛 TESTES DE REGRESSÃO

### Verificar Correção PR18 (Auto-Aprovação NAO_SUPER)

- [ ] Criar solicitação com projeto SUPER → **deve ficar pendente**
- [ ] Criar solicitação com projeto NAO_SUPER → **deve ser auto-aprovada**
- [ ] Solicitações SUPER aparecem em /aprovacoes → **sim**
- [ ] Solicitações NAO_SUPER aparecem em /aprovacoes → **não**
- [ ] Ambas aparecem em /pre-agenda após aprovadas → **sim**

### Verificar PA-06 (Botões Ocultos)

- [ ] Logar como usuário SEM grupo Superintendência
- [ ] Acessar /aprovacoes
- [ ] **Verificar**: Botões "Aprovar" e "Reprovar" **não aparecem**

---

## 📝 RELATÓRIO DE BUGS

Use esta seção para documentar quaisquer problemas encontrados durante os testes:

### Bug 1: [Título]
- **Página**:
- **Passos para Reproduzir**:
- **Resultado Esperado**:
- **Resultado Atual**:
- **Screenshot**:

---

## ✅ RESUMO DOS TESTES

**Data**: _____/_____/_____
**Testado por**: _______________

**Páginas Testadas**:
- [ ] / (Home)
- [ ] /solicitacoes
- [ ] /solicitacoes/nova
- [ ] /aprovacoes
- [ ] /pre-agenda
- [ ] /mapa-brasil

**Fluxos Testados**:
- [ ] Fluxo SUPER completo
- [ ] Fluxo NAO_SUPER completo

**Status Geral**:
- [ ] ✅ Todos os testes passaram
- [ ] ⚠️ Alguns problemas encontrados (ver relatório de bugs)
- [ ] ❌ Falhas críticas encontradas

**Observações**:
_______________________________________________
_______________________________________________
_______________________________________________
