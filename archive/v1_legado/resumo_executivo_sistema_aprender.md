# 📋 RELATÓRIO COMPLETO DO SISTEMA APRENDER

## 🎯 VISÃO GERAL

**Nome**: Sistema Aprender  
**Descrição**: Sistema de gestão de formações educacionais  
**Objetivo**: Centralizar e gerenciar solicitações de eventos, formadores e disponibilidade  
**Público-alvo**: Coordenadores, formadores e gestores educacionais  

---

## 🏗️ ARQUITETURA

### **Padrão Arquitetural**
- **Estilo**: Monolítica com separação de responsabilidades
- **Padrão**: MVC (Model-View-Controller)
- **Containerização**: Docker + Docker Compose

### **Camadas do Sistema**
1. **Apresentação**: Django Templates + Bootstrap + JavaScript
2. **Negócio**: Django Views + Services + Models
3. **Dados**: Django ORM + PostgreSQL + Redis

---

## 🔧 TECNOLOGIAS

### **Backend**
- **Framework**: Django 4.2+
- **Linguagem**: Python 3.13
- **Banco de Dados**: PostgreSQL
- **Cache**: Redis
- **ORM**: Django ORM

### **Frontend**
- **Templates**: Django Templates
- **CSS**: Bootstrap 5
- **JavaScript**: Vanilla JS + Chart.js + D3.js
- **Mapas**: D3.js + GeoJSON
- **Gráficos**: Chart.js

### **Infraestrutura**
- **Containerização**: Docker + Docker Compose
- **Servidor Web**: Nginx
- **Processo Gerenciador**: Gunicorn
- **Deployment**: Render.com

### **Integração**
- **Google Sheets**: Google Sheets API v4
- **Google Calendar**: Google Calendar API v3
- **Autenticação**: OAuth2 + Service Account

---

## 📊 MODELOS DE DADOS

### **Usuario**
- **Descrição**: Modelo de usuário customizado
- **Campos**: username, email, first_name, last_name, is_active
- **Relacionamentos**: Solicitacao, DisponibilidadeFormadores

### **Solicitacao**
- **Descrição**: Solicitações de eventos/formações
- **Campos**: titulo_evento, data_evento, municipio, projeto, status
- **Relacionamentos**: Usuario, Municipio, Projeto

### **Municipio**
- **Descrição**: Municípios onde ocorrem as formações
- **Campos**: nome, uf, regiao
- **Relacionamentos**: Solicitacao, Formador

### **Projeto**
- **Descrição**: Projetos educacionais
- **Campos**: nome, descricao, ativo
- **Relacionamentos**: Solicitacao

### **Formador**
- **Descrição**: Formadores que ministram as formações
- **Campos**: nome, email, municipio, ativo
- **Relacionamentos**: Usuario, Municipio, DisponibilidadeFormadores

### **DisponibilidadeFormadores**
- **Descrição**: Disponibilidade dos formadores
- **Campos**: formador, data_inicio, data_fim, tipo_bloqueio
- **Relacionamentos**: Formador

---

## ⚙️ FUNCIONALIDADES PRINCIPAIS

### **1. Autenticação e Autorização**
- Sistema de login/logout
- Perfis de usuário
- Controle de permissões
- Integração OAuth2

### **2. Gestão de Solicitações**
- Formulário de solicitação de eventos
- Lista de solicitações
- Sistema de aprovação
- Rastreamento de status

### **3. Dashboard Executivo**
- Mapa interativo do Brasil
- Gráficos e estatísticas
- Filtros por período e região
- Métricas em tempo real

### **4. Gestão de Formadores**
- Lista de formadores
- Controle de disponibilidade
- Sistema de bloqueios
- Integração com Google Calendar

### **5. Integração Google**
- Extração de dados do Google Sheets
- Sincronização com Google Calendar
- APIs OAuth2
- Processamento em tempo real

### **6. Relatórios**
- Relatórios executivos
- Análises de dados
- Exportação para Excel
- Dashboards personalizados

---

## 🧠 LÓGICAS DE NEGÓCIO

### **Aprovação de Eventos**
- Eventos da aba "Super" dependem da planilha de Disponibilidade
- Eventos de outras abas são aprovados por padrão
- Status: APROVADO, PENDENTE, REJEITADO

### **Mapeamento de Coordenadores**
- Coordenadores são mapeados por município
- Nomes genéricos são substituídos por nomes reais
- Fallback para nomes genéricos quando necessário

### **Disponibilidade de Formadores**
- Formadores podem ter bloqueios totais ou parciais
- Disponibilidade é verificada por data
- Integração com Google Calendar

### **Agrupamento de Dados**
- Dados são agrupados por município, projeto, coordenador
- Consolidação de eventos duplicados
- Cálculo de estatísticas agregadas

---

## 🔗 INTEGRAÇÕES

### **Google Sheets**
- **Planilhas**: Acompanhamento de Agenda, Disponibilidade, Controle, Usuários
- **Autenticação**: OAuth2 + Service Account
- **Funcionalidades**: Extração em tempo real, sincronização automática

### **Google Calendar**
- **Funcionalidades**: Sincronização de eventos, verificação de disponibilidade
- **Autenticação**: OAuth2
- **Implementação**: core/services/google_calendar.py

### **APIs Internas**
- **Endpoints**: /api/mapa/dados/, /api/estatisticas/, /diretoria/api/coordenadores/
- **Tecnologias**: Django REST Framework, JSON
- **Implementação**: api/views.py, core/views/diretoria_views.py

---

## 🚀 DEPLOYMENT

### **Ambiente de Desenvolvimento**
- Docker + Docker Compose
- PostgreSQL local
- Redis local
- Hot reload habilitado

### **Serviços**
- **Web**: Django + Gunicorn + Nginx (porta 8000)
- **Database**: PostgreSQL 15 (porta 5433)
- **Cache**: Redis 7 (porta 6379)
- **MCP**: MCP Server (porta 3001)
- **Streamlit**: Streamlit (porta 8501)

### **Produção**
- **Plataforma**: Render.com
- **Configuração**: render.yaml
- **Database**: PostgreSQL (Render)
- **Buildpack**: Python

---

## 📊 TIPOS DE DADOS

### **Solicitações**
- **Volume**: ~2.000 registros
- **Fonte**: Google Sheets + Sistema
- **Campos**: titulo_evento, data_evento, municipio, projeto, coordenador

### **Usuários**
- **Volume**: ~200 registros
- **Fonte**: Sistema + Google Sheets
- **Campos**: username, email, first_name, last_name, is_active

### **Municípios**
- **Volume**: ~100 registros
- **Fonte**: Sistema
- **Campos**: nome, uf, regiao

### **Formadores**
- **Volume**: ~50 registros
- **Fonte**: Sistema + Google Sheets
- **Campos**: nome, email, municipio, ativo

### **Disponibilidade**
- **Volume**: ~500 registros
- **Fonte**: Sistema + Google Calendar
- **Campos**: formador, data_inicio, data_fim, tipo_bloqueio

---

## 🔄 FLUXO PRINCIPAL

1. **Coordenador** cria solicitação de evento
2. **Sistema** valida dados e verifica disponibilidade
3. **Solicitação** é enviada para aprovação
4. **Gestor** aprova ou rejeita solicitação
5. **Evento** é criado no Google Calendar
6. **Formadores** são notificados

---

## 👥 CASOS DE USO

### **Coordenador**
- Criar solicitação de evento
- Visualizar status das solicitações
- Gerenciar formadores do município

### **Formador**
- Visualizar disponibilidade
- Gerenciar bloqueios
- Ver eventos atribuídos

### **Gestor**
- Aprovar/rejeitar solicitações
- Visualizar dashboard executivo
- Gerar relatórios

---

## ⚙️ CONFIGURAÇÃO

### **Variáveis de Ambiente**
- DATABASE_URL
- SECRET_KEY
- GOOGLE_SHEETS_CREDENTIALS
- GOOGLE_CALENDAR_CREDENTIALS

### **Dependências Principais**
- Django 4.2+
- PostgreSQL
- Redis
- Google APIs Client
- Docker
- Nginx

---

## 📈 MÉTRICAS DO SISTEMA

### **Dados Extraídos das Planilhas**
- **Total**: 72.251 registros
- **Abas**: 30
- **Planilhas**: 4

### **Distribuição por Categoria**
- **Controle 2025**: 61.077 registros (84.5%)
- **Agenda 2025**: 9.698 registros (13.4%)
- **Disponibilidade 2025**: 1.336 registros (1.8%)
- **Usuários**: 140 registros (0.2%)

---

## 🎯 CONCLUSÃO

O **Sistema Aprender** é uma solução completa de gestão de formações educacionais que integra múltiplas fontes de dados, oferece dashboards executivos e automatiza processos de aprovação e disponibilidade. O sistema é robusto, escalável e bem documentado, permitindo que qualquer IA possa entender completamente seu contexto e funcionalidades.

**Status**: ✅ Sistema funcional e em produção  
**Documentação**: ✅ Completa e atualizada  
**Integração**: ✅ Google Sheets + Google Calendar  
**Deployment**: ✅ Docker + Render.com  
