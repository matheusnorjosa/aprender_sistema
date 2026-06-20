# Planilhas → Sistema: Guia de Migração

## Objetivo da Fase 5

A **Fase 5** tem como objetivo principal facilitar o **desligamento gradual das planilhas Google Sheets/Excel** como fonte de verdade (SSOT) do sistema, transferindo essa responsabilidade para o banco de dados PostgreSQL do AS v2.

Este documento descreve:
1. Como o endpoint `/api/etl/reports/latest/` facilita a observabilidade do ETL
2. Estratégias para migrar processos que ainda dependem de planilhas
3. Roadmap de substituição planilha → sistema

---

## 1. Observabilidade de ETL

### 1.1. Problema

Antes da Fase 5, os relatórios ETL eram gerados em `out_etl/` mas não havia forma prática de:
- Listar quais arquivos foram gerados recentemente
- Ver metadados (tamanho, data, tipo)
- Acessar relatórios via API (sem SSH no servidor)

### 1.2. Solução: Endpoint `/api/etl/reports/latest/`

**Backend implementado** ✅:
- **Service Layer**: `apps/dat_ingest/services/etl_observability.py`
  - Função `list_latest_reports(limit=20)`: Varre `ETL_OUTPUT_DIR`, ordena por mtime desc
  - Função `get_report_path(filename)`: Retorna path absoluto com validação de segurança
- **View**: `EtlReportsLatestView` (GET, requer permissão `IsControleOrSuper`)
- **Rota**: `GET /api/etl/reports/latest/?limit=20`
- **Segurança**:
  - Valida `limit` (1-100)
  - Previne path traversal (`../`, caminhos absolutos)
  - Trata diretório ausente como lista vazia (não erro)
  - Ignora arquivos ocultos e subdiretórios

**Exemplo de resposta**:
```json
{
  "count": 3,
  "limit": 20,
  "reports": [
    {
      "filename": "acoes_dat_2025-10-30.json",
      "size_bytes": 15420,
      "mtime_iso": "2025-10-30T14:23:45",
      "kind": "json",
      "path_rel": "acoes_dat_2025-10-30.json"
    },
    {
      "filename": "acompanhamento_2025-10-29.csv",
      "size_bytes": 8921,
      "mtime_iso": "2025-10-29T09:15:32",
      "kind": "csv",
      "path_rel": "acompanhamento_2025-10-29.csv"
    }
  ]
}
```

**Frontend** ✅ **(Completo - 2025-10-31)**:
- Página `/controle/etl-reports` com tabela listando arquivos
- Colunas: Nome (com ícone), Tipo (tag colorida), Tamanho (formatado), Data/Hora, Ações (download)
- Filtros: tipo de arquivo (todos/json/csv/txt/outro), limite (1-100), botão atualizar
- Download individual: link direto para `/out_etl/{filename}` em nova aba
- Permissões: Controle ou Superintendência
- Menu: item "Relatórios ETL" no sidebar principal

**Como usar**:
1. Acesse `/controle/etl-reports` no sistema (menu lateral → Relatórios ETL)
2. Use filtros para visualizar apenas relatórios específicos (ex: apenas JSON)
3. Ajuste o limite para ver mais/menos arquivos
4. Clique em "Download" para baixar um relatório individual
5. Relatórios são gerados automaticamente pelos comandos ETL (ver seção 4.1)

---

## 2. Estratégia de Migração: Planilhas → Sistema

### 2.1. Princípios

1. **SSOT Único**: Banco de dados PostgreSQL é a única fonte de verdade
2. **Planilhas Read-Only**: Gradualmente transformar planilhas em visualizações (dashboards) do sistema
3. **ETL Bidirecional**: Permitir importação (planilha → BD) e exportação (BD → planilha) temporariamente
4. **Formulários no Sistema**: Substituir edições manuais em planilhas por formulários web

### 2.2. Roadmap de Substituição

#### **Fase A: Observabilidade** ✅ **(Completo em 2025-10-30)**
- [x] Endpoint `/api/etl/reports/latest/` (backend)
- [ ] Painel frontend `/etl-reports`

#### **Fase B: Solicitações de Eventos** ✅ **(Completo em Fases 1-4)**
- [x] Formulário web para criar solicitações
- [x] Fluxo de aprovação (SUPER/NAO_SUPER)
- [x] Integração Google Calendar (publish/resync/cancel)
- [x] Planilha "Acompanhamento de Agenda" → **Read-Only** (dados vêm do sistema)

#### **Fase C: Cadastros (DAT)** ✅ **(Completo em Fase 1)**
- [x] CRUD de Usuários, Grupos, Municípios, Projetos via Admin DAT
- [x] Planilhas "Usuários.xlsx", "Municípios", "Projetos" → **Read-Only**

#### **Fase D: Compras (Controle)** ⏳ **(Planejado para Fase 6)**
- [ ] Página de importação de planilhas Excel/CSV (Controle)
- [ ] Página de consulta/filtro de compras
- [ ] Planilha "Controle - COMPRAS" → **Read-Only**

#### **Fase E: Disponibilidade de Formadores** ⏳ **(Futuro)**
- [ ] Formulário para formadores bloquearem agenda (parcial/total)
- [ ] Visualização de calendário mensal (grade de disponibilidade)
- [ ] Planilha "Disponibilidade_2025.xlsx" → **Read-Only**

#### **Fase F: Deslocamentos** ⏳ **(Futuro)**
- [ ] Formulário para registrar deslocamentos
- [ ] Relatórios de deslocamentos por período/formador
- [ ] Aba "DESLOCAMENTO" → **Read-Only**

---

## 3. Como Entradas Alimentam o Sistema

### 3.1. Fluxo Atual (Fase 5 - Backend Completo)

```
┌──────────────────────────────────────────┐
│  Planilhas Google Sheets/Excel           │
│  (Acompanhamento, Controle, Usuários)    │
└────────────┬─────────────────────────────┘
             │
             │ (1) ETL Manual (management commands)
             │     python manage.py etl_upsert_*
             v
┌──────────────────────────────────────────┐
│  Banco PostgreSQL (AS v2)                 │
│  - Solicitacao, Usuario, Municipio, etc. │
└────────────┬─────────────────────────────┘
             │
             │ (2) API REST
             │     /api/solicitacoes/
             │     /api/usuarios-admin/
             v
┌──────────────────────────────────────────┐
│  Frontend React (Vite)                    │
│  - Formulários, listagens, aprovações    │
└──────────────────────────────────────────┘
             │
             │ (3) Integração Externa
             │     Google Calendar API
             v
┌──────────────────────────────────────────┐
│  Google Calendar (Eventos publicados)    │
└──────────────────────────────────────────┘
```

### 3.2. Fluxo Futuro (Após Fase 6)

```
┌──────────────────────────────────────────┐
│  Frontend React (Entrada Principal)      │
│  - Formulários para todas as entidades   │
│  - Importação de planilhas (opcional)    │
└────────────┬─────────────────────────────┘
             │
             │ API REST (única interface)
             v
┌──────────────────────────────────────────┐
│  Banco PostgreSQL (SSOT Único)           │
│  - Todas as entidades vivem aqui         │
└────────────┬─────────────────────────────┘
             │
             ├──> (Exportação Read-Only)
             │    Planilhas como dashboards
             │
             └──> (Integração Externa)
                  Google Calendar, relatórios, etc.
```

---

## 4. Comandos ETL Disponíveis

### 4.1. Importação de Dados

| Comando | Origem | Destino | Status |
|---------|--------|---------|--------|
| `etl_upsert_acompanhamento` | `Acompanhamento de Agenda _2025.xlsx` | `Solicitacao` | ✅ Funcionando |
| `etl_upsert_deslocamento` | `Disponibilidade_2025.xlsx` (aba DESLOCAMENTO) | `Deslocamento` | ✅ Funcionando |
| `import_usuarios_from_csv` | `Usuários.xlsx` → CSV | `Usuario` | ✅ Funcionando |
| `etl_import_acoes_controle` | `Planilha de Controle - 2025.xlsx` (aba AÇÕES) | `AcaoControle` | ✅ Funcionando |
| `etl_import_dat_cadastros` | `Planilha de Controle - 2025.xlsx` (aba DAT) | `AcaoDAT` | ✅ Funcionando |

### 4.2. Relatórios ETL

Todos os comandos acima geram relatórios JSON em `ETL_OUTPUT_DIR` (default: `v2/backend/out_etl/`).

**Listar relatórios via API**:
```bash
curl -H "Authorization: Bearer <token>" \
  http://localhost:8002/api/etl/reports/latest/?limit=10
```

**Listar relatórios via Django shell**:
```python
from apps.dat_ingest.services.etl_observability import list_latest_reports

reports = list_latest_reports(limit=10)
for r in reports:
    print(f"{r['filename']} ({r['kind']}) - {r['mtime_iso']}")
```

---

## 5. Próximos Passos

### Curto Prazo (Fase 5 - Frontend)
1. ✅ Backend endpoint `/api/etl/reports/latest/` **(Completo)**
2. ⏳ Página React `/etl-reports` para grupos Controle/Superintendência
3. ⏳ Download individual de relatórios via API

### Médio Prazo (Fase 6 - Compras)
1. Página de importação de planilhas Excel/CSV (Controle)
2. Página de consulta de compras com filtros
3. Documentação do fluxo de importação

### Longo Prazo (Fases 7+)
1. Formulários web para disponibilidade de formadores
2. Formulários web para deslocamentos
3. Dashboards de visualização (substituem planilhas como visualizações)
4. Exportação automática BD → Sheets (read-only) para usuários não-técnicos

---

## 6. Contribuindo

Para adicionar novos endpoints ou funcionalidades de observabilidade:

1. **Service Layer**: `apps/dat_ingest/services/etl_observability.py`
2. **Views**: `apps/dat_ingest/views.py`
3. **URLs**: `apps/dat_ingest/urls.py`
4. **Testes**: `apps/dat_ingest/tests/test_etl_*.py`
5. **Documentação**: Atualizar este arquivo (PLANILHAS_TO_SYSTEM.md)

**Referência**:
- [PLANO_DAT_GCAL_2025-10-29.md](./PLANO_DAT_GCAL_2025-10-29.md) - Roadmap completo
- [GUIDE_GCAL.md](./GUIDE_GCAL.md) - Guia de integração Google Calendar

---

**Última atualização**: 2025-10-30 (Fase 5 - Backend completo)
