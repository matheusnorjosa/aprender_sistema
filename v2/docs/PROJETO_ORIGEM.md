# Documento Consolidado — Projeto Aprender Sistema (AS)

## 1. Origem do Projeto: Lógica das Planilhas
O sistema original funcionava integralmente sobre planilhas Google/Excel, que acumulavam regras complexas de negócio. O novo sistema busca substituir essas planilhas por uma plataforma web automatizada.

### 1.1 Planilhas Originais
- Disponibilidade_2025.xlsx
- Planilha de Controle - 2025.xlsx
- Usuários.xlsx
- Produtos.xlsx

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

## 2. O Novo Sistema (Aprender Sistema - AS)

### 2.1 Tecnologias
- **Backend**: Python 3.11 (imagem base) + Django 5.1.x + DRF + Celery (worker e beat)
- **Banco de Dados**: PostgreSQL 15
- **Cache & Filas**: Redis 7 (cache e broker Celery)
- **Infraestrutura**: Docker + Docker Compose (`v2/infra/docker-compose.yml`) orquestrado via `make`
- **Frontend**: React (Vite) + Tailwind + Ant Design; build Docker-first e dev server com proxy `/api`

### 2.2 Estrutura de Código
- **Backend (`v2/backend`)**
  - Apps: `apps.core` (domínio principal) e `apps.dat_ingest` (ETLs e ingestão)
  - Configurações Django em `config/`
  - Comandos ETL em `apps/dat_ingest/management/commands`
- **Frontend (`v2/frontend`)**
  - Projeto React com Vite, Tailwind e Ant Design
  - Páginas: Pré-agenda, Grade Mensal (Formadores/Coordenadores), painéis Controle/DAT

**Modelos principais**:
- Usuario → usuários do sistema
- Formador → instrutores com disponibilidade e área de atuação
- Projeto → agrupamento de ações
- Municipio → municípios atendidos
- TipoEvento → classificações dos eventos
- Solicitacao → pedido de evento
- Aprovacao → status de análise de uma solicitação
- Deslocamento → registros de deslocamentos
- DisponibilidadeFormador → agenda consolidada
- LogAuditoria → rastreamento de ações

**ETLs**: Management commands para Acompanhamento, Deslocamento, Ações (Controle) e Cadastros (DAT) com suporte a `--dry-run` e relatórios em `out_etl/`

### 2.3 Funcionalidades Atuais
- Autenticação e RBAC via Django (grupos: Superintendência, Controle, Coordenador, Formador, DAT, Gerência)
- API REST: `/api/solicitacoes/`, `/api/availability/monthly/`, `/api/controle/acoes/`, `/api/dat/acoes/`, `/api/features/`, `/api/me/`
- Pré-agenda React: fluxo de approve/reject (Superintendência) e preview/publish (Controle) respeitando `apply_blocked`
- Grade Mensal React com duas grades (Formadores/Coordenadores), filtros compartilhados, detalhes por célula e export CSV
- ETLs CSV/XLSX com relatórios em `out_etl/*.json` e idempotência por `external_hash`
- Integração Google Calendar real (`asv2-{id}`, `sendUpdates='none'`) com fallback fake controlado por feature flags

---

## 3. Papéis, Perfis e Autorizações

### 3.1 Perfis de Usuário
- **Superintendência**: autoriza/reprova solicitações, resolve conflitos, valida agenda final
- **Coordenadores**: podem solicitar eventos, mas não aprovar
- **Formadores**: podem bloquear sua agenda (parcial/total), mas não solicitam/aprovam eventos

### 3.2 Fluxo de Autorização
1. Coordenador envia solicitação.
2. Sistema checa disponibilidade do formador (conflitos, bloqueios, deslocamentos).
3. Se sem conflito → solicitação vai para Superintendência.
4. Superintendência aprova → cria evento no Google Calendar.
5. Superintendência reprova → retorna com justificativa.

---

## 4. Requisitos Funcionais (RFs)
- RF01: Importação de dados (usuários, municípios, projetos, tipos de evento, produtos).
- RF02: Solicitação de eventos.
- RF03: Verificação de conflitos (sobreposição, deslocamentos, bloqueios).
- RF04: Fluxo de aprovações com controle de perfis.
- RF05: Integração com Google Calendar.
- RF06: Criação automática de link Google Meet.
- RF07: Auditoria de todas as operações críticas.
- RF08: Interface de mapa mensal (disponibilidade).

---

## 5. Integrações Externas
- **Google Calendar API**
  - Credenciais no Google Cloud
  - Evento aprovado → gera evento no calendário
  - Evento gera link Meet automaticamente via API

---

## 6. Situação Atual vs. Próximos Passos

✅ Concluído até agora:
- Estrutura base Django + PostgreSQL em Docker
- Modelos principais criados
- Migrações aplicadas
- Importação inicial de formadores concluída
- API de disponibilidades + página de visualização
- Cadastro de bloqueio de agenda
- Solicitação de eventos simples
- Fluxo de aprovações iniciado
- Home consolidando links
- **PR16**: RF03 - Verificação de Conflitos (17 testes passando)
- **PR17**: PA-01 a PA-07 - Política de Aprovação Manual (5 testes passando, frontend conforme)

🚧 Próximos Passos:
- Criar scripts de importação para municípios, projetos, tipos de evento
- ~~Implementar RF03 (checagem automática de conflitos)~~ ✅ Completo (PR16)
- ~~Finalizar RF04 (workflow completo de aprovações)~~ ✅ PA-01 a PA-07 completo (PR17)
- Conectar com Google Calendar API (RF05/RF06)
- Implementar testes end-to-end (Playwright)
- Refinar interface (baseada em mapa mensal como referência)

---

## 6.1. Importação de Usuários e Grupos

**Estrutura da Planilha (Acompanhamento de Agenda):**
- Coluna **N**: Coordenador
- Colunas **O-S**: Formador 1, Formador 2, ..., Formador 5

**Regra de Atribuição de Grupos:**
- Usuários com username `coordenacao*` → Grupo "Coordenador"
- Demais usuários com participações → Grupo "Formador"

**Comando de Backfill:**
```bash
python manage.py backfill_user_groups --apply
```
- Atribui grupos faltantes baseado no padrão do username
- Usado após importação inicial de usuários (122 usuários importados)
- Resultado: 65 Formadores + 10 Coordenadores atribuídos corretamente

---

## 7. Benefícios Esperados
- Fim da dependência de planilhas manuais
- Fluxo de solicitações, aprovações e conflitos totalmente digital
- Registro auditável e confiável das agendas
- Integração automática com Google Calendar e Meet
- Escalabilidade para múltiplos anos e centenas de formadores
