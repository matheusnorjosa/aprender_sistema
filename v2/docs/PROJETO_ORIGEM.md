# Documento Consolidado — Projeto Aprender Sistema (AS)

> **Última atualização**: Janeiro 2026
> **Versão do Sistema**: 2.0 (Produção)

## 1. Origem do Projeto: Lógica das Planilhas

O sistema original funcionava integralmente sobre planilhas Google/Excel, que acumulavam regras complexas de negócio. O AS v2 substitui essas planilhas por uma plataforma web automatizada.

### 1.1 Planilhas Originais
- Acompanhamento de Agenda _ 2025.xlsx
- Disponibilidade _ 2025.xlsx
- Planilha de Controle - 2025.xlsx
- Usuários.xlsx

### 1.2 Regras de Negócio Embutidas
- **Códigos de Disponibilidade**
  - E → Evento confirmado
  - M → Mais de um evento
  - D → Deslocamento
  - P → Bloqueio parcial
  - T → Bloqueio total
  - X → Conflito

- **Verificação de Disponibilidade**: fórmulas cruzadas verificavam automaticamente se o formador podia ser agendado.
- **Consistência de Dados**: uso de IMPORTRANGE e referências cruzadas para manter sincronizados nomes de usuários, municípios e tipos de eventos.

- **Fluxo Operacional**:
  1. Solicitação feita por coordenadores em uma planilha.
  2. Verificação manual de disponibilidade e conflitos.
  3. Aprovação (ou reprovação) pela Superintendência.
  4. Lançamento no Google Calendar manual.

---

## 2. O Novo Sistema (Aprender Sistema - AS v2)

### 2.1 Tecnologias
- **Backend**: Python 3.12 + Django 5.2 + DRF + Celery (worker e beat)
- **Banco de Dados**: PostgreSQL 15
- **Cache & Filas**: Redis 7 (cache e broker Celery)
- **Infraestrutura**: Docker + Docker Compose (`v2/infra/docker-compose.yml`)
- **Frontend**: React (Vite) + Tailwind + Ant Design
- **Type Checking**: Pyright (strict mode)
- **Testes E2E**: Playwright (46 testes)

### 2.2 Estrutura de Código

#### Backend (`v2/backend`)
- **Apps**: `apps.core` (domínio principal) e `apps.dat_ingest` (ETLs e ingestão)
- **Configurações**: `config/` (settings, urls, wsgi, celery)
- **Comandos ETL**: `apps/dat_ingest/management/commands/` (21 comandos)

#### Frontend (`v2/frontend`)
- **Framework**: React 18 + Vite 7
- **UI**: Ant Design 5 + Tailwind CSS
- **Páginas**: 45+ páginas organizadas em módulos

### 2.3 Modelos do Sistema (28 modelos)

#### Usuários e Organização
| Modelo | Descrição |
|--------|-----------|
| `Usuario` | Usuário do sistema (extends AbstractUser) |
| `Gerencia` | Gerências da organização |
| `ProjetoGeral` | Projetos gerais da organização |
| `EquipeGerencia` | Relação usuário-gerência |

#### Solicitações e Agenda
| Modelo | Descrição |
|--------|-----------|
| `Solicitacao` | Pedido de evento (status: pendente/aprovado/reprovado) |
| `Participation` | Participantes de uma solicitação (role: COORDENADOR/FORMADOR/APOIO) |
| `AvailabilityBlock` | Bloqueios de agenda (tipos: P=parcial, T=total) |
| `Deslocamento` | Registros de deslocamentos entre municípios |

#### Domínio Principal
| Modelo | Descrição |
|--------|-----------|
| `Projeto` | Projetos (fluxo: SUPER/NAO_SUPER) |
| `Municipio` | Municípios atendidos |
| `TipoEvento` | Classificações de eventos |

#### Módulo DAT (Departamento de Apoio Técnico)
| Modelo | Descrição |
|--------|-----------|
| `DATAcao` | Ações do DAT (workflow: NOT_STARTED→IN_PROGRESS→COMPLETED→ARCHIVED) |
| `DATRegistro` | Registros de turmas |
| `DATCadastro` | Cadastros em plataformas (etapas: ABERTA→COLETA→PREENCHIMENTO→REVISAO→FINALIZADA) |
| `DATCompra` | Compras de materiais |
| `DATCoordenador` | Coordenadores DAT |
| `DATFormacao` | Formações DAT |
| `DATArea` | Áreas de atuação DAT |

#### Módulo PlanoFormações
| Modelo | Descrição |
|--------|-----------|
| `PlanoFormacoes` | Plano anual de formações |
| `Formacao` | Formação individual |
| `Acompanhamento` | Acompanhamento de formação |
| `Prova` | Provas/avaliações |

#### Controle e Compras
| Modelo | Descrição |
|--------|-----------|
| `AcaoControle` | Ações do setor Controle |
| `AcaoDAT` | Ações DAT (legado) |
| `Compra` | Registro de compras |
| `Produto` | Produtos para compra |

#### Sistema e Auditoria
| Modelo | Descrição |
|--------|-----------|
| `Config` | Configurações do sistema |
| `AuditLog` | Log de auditoria (todas operações críticas) |
| `GoogleOAuthCredential` | Credenciais OAuth criptografadas |

### 2.4 Importação de Dados

> **Atualizado (SDD 2026-06).** O antigo pipeline ETL (`apps.dat_ingest`, ~21 comandos `import_*` como
> `import_municipios`/`import_usuarios`/`import_dat_*`) foi **removido** (#967/#971). Aquela lista não reflete
> mais o sistema.

A importação hoje usa o pipeline **export-contract** (`apps/core/imports/`), idempotente por `external_hash`
SHA1 (ADR-012), **dry-run por padrão**. Único management command real: `import_export_contract`. Também há
endpoints DRF (`POST /api/<recurso>/import/`).

Contratos por entidade e ordem de importação: `v2/docs/imports/README.md`.

---

## 3. Papéis, Perfis e Autorizações (RBAC)

### 3.1 Grupos de SETOR (onde trabalha)
- Superintendência, DAT, Controle, Vidas, ACerta, Brincando, Fluir, Sou da Paz, Gerência

### 3.2 Grupos de FUNÇÃO (o que pode fazer)
- **Formador**: Visualiza grade, gerencia bloqueios pessoais
- **Coordenador**: Cria solicitações de eventos
- **Apoio de Coordenação**: Auxilia coordenação
- **Gerente**: Aprova/reprova, acessa dashboards

### 3.3 Fluxos de Aprovação

#### Fluxo SUPER (Requer Aprovação Manual)
1. Coordenador envia solicitação → `status = pendente`
2. Sistema checa disponibilidade (RD-01 a RD-08)
3. Superintendência aprova/reprova
4. Se aprovado → Controle publica no Google Calendar

#### Fluxo NAO_SUPER (Auto-Aprovado)
1. Coordenador envia solicitação → `status = aprovado` (automático)
2. Vai direto para Controle publicar

---

## 4. Requisitos Funcionais (RFs)

| RF | Descrição | Status |
|----|-----------|--------|
| RF01 | Importação de dados (usuários, municípios, projetos) | ✅ Completo |
| RF02 | Solicitação de eventos | ✅ Completo |
| RF03 | Verificação de conflitos (RD-01 a RD-08) | ✅ Completo |
| RF04 | Fluxo de aprovações (PA-01 a PA-07) | ✅ Completo |
| RF05 | Integração com Google Calendar | ✅ Completo |
| RF06 | Criação automática de link Google Meet | ✅ Completo |
| RF07 | Auditoria de operações críticas | ✅ Completo |
| RF08 | Interface de grade mensal | ✅ Completo |

---

## 5. Regras de Negócio Implementadas

### 5.1 Regras de Disponibilidade (RD-01 a RD-08)
- **RD-01**: Não-sobreposição (overlap ≥1min = conflito)
- **RD-02**: Bloqueio total (T) impede eventos
- **RD-03**: Bloqueio parcial (P) impede no subintervalo
- **RD-04**: Buffer de deslocamento (D) entre municípios
- **RD-05**: Capacidade diária (M) por formador
- **RD-06**: Timezone America/Fortaleza (armazena UTC)
- **RD-07**: Prioridade: Bloqueios → Conflitos → Buffer → Limite
- **RD-08**: Mensagens estruturadas com código/tipo

### 5.2 Política de Aprovação (PA-01 a PA-07)
- **PA-01**: Projetos SUPER nunca auto-aprovam
- **PA-02**: Superintendência/DAT/superuser podem aprovar
- **PA-03**: Integrações executam após aprovação
- **PA-04**: Estado inicial = pendente (SUPER) ou aprovado (NAO_SUPER)
- **PA-05**: Auditoria em AuditLog
- **PA-06**: UI esconde ações sem permissão
- **PA-07**: Testes obrigatórios de conformidade

---

## 6. Integrações Externas

### Google Calendar API
- Credenciais via Service Account ou OAuth
- Eventos aprovados → criados no calendário
- Google Meet link gerado automaticamente
- `sendUpdates` configurável (none/all/externalOnly)
- Fallback para cliente fake em desenvolvimento

---

## 7. Observabilidade

### Prometheus + Grafana (Opcional)
- Métricas: HTTP requests, latência, error rate, cache hit rate
- Dashboard "AS v2 - System Overview"

### Structured Logging
- JSON em staging/production
- Correlation ID (request_id) para rastreamento
- Service identification (web/worker/beat)

---

## 8. Portas e URLs

| Serviço | Porta | URL |
|---------|-------|-----|
| Frontend | 5173 | http://localhost:5173 |
| Backend API | 8002 | http://localhost:8002/api/ |
| PostgreSQL | 5434 | localhost:5434 |
| Redis | 6380 | localhost:6380 |

---

## 9. Cobertura de Testes

| Área | Testes | Status |
|------|--------|--------|
| Availability Service (RD-01→RD-08) | 17 | ✅ |
| Approval Policy (PA-01→PA-07) | 5 | ✅ |
| RBAC Permissions | 20+ | ✅ |
| Google Calendar | 6+ | ✅ |
| ETL Imports | 40+ | ✅ |
| E2E Playwright | 46 | ✅ |

---

## 10. Referências

- **CLAUDE.md**: Regras completas e cláusulas pétreas
- **GUIDE_GCAL.md**: Integração Google Calendar
- **RBAC_COMPLETO.md**: Sistema de permissões
- **TESTING_POLICY.md**: Políticas de teste
- **OBSERVABILITY.md**: Prometheus/Grafana/Logging
