# 🎯 CODEX CONTEXT PACKAGE - Projeto Aprender Sistema

## 📋 RESUMO EXECUTIVO

**O que é**: Sistema Django que substitui planilhas por workflow digital para gestão de eventos educacionais
**Objetivo**: Solicitação → Aprovação → Criação automática no Google Calendar
**Stack**: Python 3.13 + Django 5.2 + PostgreSQL 15 + Docker
**Status**: ✅ SISTEMA OPERACIONAL com dados reais

## 🔢 ESTADO ATUAL (Setembro 2025)

### Dados Reais Importados:
- **1.915 solicitações** (2025-01-29 a 2025-12-05)
- **88 formadores** ativos
- **74 municípios** cadastrados
- **24 projetos** configurados
- **20 tipos de evento** disponíveis

### Distribuição por Projetos:
1. **ACerta**: 426 eventos (22%)
2. **Novo Lendo**: 399 eventos (21%)
3. **Tema**: 287 eventos (15%)
4. **Lendo e Escrevendo**: 179 eventos (9%)
5. **Brincando e Aprendendo**: 150 eventos (8%)
6. **Vida & Matemática**: 107 eventos (6%)
7. **Vida & Linguagem**: 101 eventos (5%)
8. **Outros 17 projetos**: 266 eventos (14%)

## 🏗️ ARQUITETURA TÉCNICA

### Stack Tecnológica:
- **Backend**: Django 5.2 (Python 3.13)
- **Database**: PostgreSQL 15 (Docker porta 5433)
- **Frontend**: Django Templates + Bootstrap + JavaScript
- **Infrastructure**: Docker Compose
- **Integrations**: Google Calendar API, Google Sheets API

### Estrutura do Projeto:
```
core/                    # App principal
├── models.py           # 15+ modelos (Usuario, Formador, Solicitacao, etc.)
├── views/              # Views organizadas por funcionalidade
├── templates/          # Templates Django
├── services/           # Lógica de negócio
└── management/commands/ # Comandos Django customizados

docs/                   # Documentação completa
├── memoria/           # Sessões e descobertas
├── security/          # Segurança e secrets
├── ops/              # Deploy e troubleshooting
└── dev/              # Setup de desenvolvimento
```

## 👥 ESTRUTURA ORGANIZACIONAL

### Perfis de Usuário:
- **Superintendência**: Aprova/reprova solicitações
- **Coordenadores**: Criam solicitações de eventos
- **Formadores**: Bloqueiam sua agenda, executam eventos
- **Controle**: Gerencia pré-agenda e conflitos

### Hierarquia Organizacional:
```
Superintendência
├── Coordenadores (Ellen Damares, Aurea Lucia, Maria Nadir, Rafael Rabelo)
├── Formadores (88 ativos)
└── Setores por Projeto (ACerta, Novo Lendo, Tema, etc.)
```

## 🔄 FLUXO DE TRABALHO

### Processo Principal:
1. **Coordenador** cria solicitação de evento
2. **Sistema** verifica conflitos (formador, município, horário)
3. **Superintendência** aprova/reprova manualmente
4. **Sistema** cria evento no Google Calendar automaticamente
5. **Auditoria** registra todas as operações

### Regras de Disponibilidade:
- **E**: Evento confirmado
- **M**: Mais de um evento (limite diário)
- **D**: Deslocamento entre municípios
- **P**: Bloqueio parcial
- **T**: Bloqueio total
- **X**: Conflito identificado

## 🐳 AMBIENTE DOCKER

### Configuração Atual:
```yaml
services:
  db: postgres:15 (porta 5433)
  web: Django (porta 8000)
  streamlit: Dashboard (porta 8501)
  mcp: MCP Server (porta 3001)
  pgadmin: Admin DB (porta 8080)
```

### Comandos Essenciais:
```bash
# Iniciar ambiente completo
docker-compose up -d

# Executar comandos Django
docker-compose exec web python manage.py [comando]

# Ver logs
docker-compose logs web

# Parar ambiente
docker-compose down
```

## 📊 FUNCIONALIDADES IMPLEMENTADAS

### ✅ Módulos Funcionais:
- **Autenticação**: Login via CPF + Django Groups
- **Solicitações**: Criação e gestão de eventos
- **Aprovações**: Workflow superintendência
- **Bloqueios**: Agenda de formadores
- **Pré-Agenda**: Controle intermediário
- **Mapa Mensal**: Visualização disponibilidade
- **Auditoria**: Logs completos de ações
- **Import/Export**: Google Sheets integration

### 🔧 Comandos Django Importantes:
```bash
# Importar dados de planilhas
python manage.py import_agenda_completa --verbose

# Analisar planilhas Google
python manage.py analyze_google_sheets

# Importar formadores
python manage.py import_formadores

# Migração de dados
python manage.py migrate
```

## 🔑 CREDENCIAIS E INTEGRAÇÕES

### Google Services:
- **Calendar API**: Configurado e funcional
- **Sheets API**: Para importação de dados
- **OAuth2**: `google_authorized_user.json`

### Environment Variables:
```bash
ENVIRONMENT=staging
DB_HOST=localhost
DB_PORT=5433
DB_NAME=aprender_sistema_db
DB_USER=adm_aprender
DB_PASSWORD=aprender123456
```

## 📁 ARQUIVOS CRÍTICOS

### Documentação Principal:
- `CLAUDE.md` - Histórico completo das sessões
- `.claude/CLAUDE.md` - Diretrizes técnicas
- `docker-compose.yml` - Configuração infraestrutura
- `core/models.py` - Estrutura de dados

### Configurações:
- `.env` - Variáveis de ambiente
- `requirements.txt` - Dependências Python
- `Dockerfile` - Imagem Docker
- `google_authorized_user.json` - OAuth Google

## 🚀 PRÓXIMOS PASSOS

### Prioridades:
1. **Finalizar Google Calendar Integration**
2. **Otimizar Performance de Consultas**
3. **Implementar Notificações Email**
4. **Deploy para Produção (Render)**
5. **Testes Automatizados Completos**

## ⚠️ INFORMAÇÕES IMPORTANTES

### Dados Sensíveis:
- **NÃO COMMITAR**: Arquivos .env, credenciais Google
- **Backup Regular**: PostgreSQL data volume
- **Auditoria**: Todas as operações são logadas

### Limitações Conhecidas:
- Windows Codex CLI tem bugs (usar WSL2)
- MCP registration temporariamente desabilitado
- Google Calendar OAuth precisa renovação periódica

## 🤝 COLABORAÇÃO CLAUDE + CODEX

### Protocolos de Trabalho:
- **Claude Code**: Especialista no histórico e contexto
- **Codex CLI**: Implementação e execução de código
- **Comunicação**: Coordenação de tarefas complementares
- **Validação**: Revisão cruzada de implementações

---

**💡 Nota**: Este é um projeto real em produção com dados confidenciais. Manter segurança e seguir princípios LGPD.