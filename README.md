# Aprender Sistema

[![CI](https://github.com/matheusnorjosa/aprender_sistema/actions/workflows/ci.yaml/badge.svg)](https://github.com/matheusnorjosa/aprender_sistema/actions/workflows/ci.yaml)
[![codecov](https://codecov.io/gh/matheusnorjosa/aprender_sistema/branch/main/graph/badge.svg)](https://codecov.io/gh/matheusnorjosa/aprender_sistema)

Este repositório armazena apenas a estrutura **v2** do Sistema Aprender.
Todo o código/documentação da versão anterior (v1) foi movido para
`archive/v1_legado/` e permanece somente para consulta histórica.

```
.
├── archive/v1_legado/   # snapshot completo do sistema legado
└── v2/                  # backend, frontend, infra e docs oficiais da v2
```

## Desenvolvimento

Trabalhe sempre dentro de `v2/`:

```bash
cd v2
make up            # sobe o stack aprender_v2
make readyz        # health check
make down          # derruba os containers
```

Compose oficial: `v2/infra/docker-compose.yml` com
`COMPOSE_PROJECT_NAME=aprender_v2`. O script `make ban-v1` remove quaisquer
containers/redes/volumes antigos com o label `aprendersistema`.

## 📚 Documentação Operacional

### 📖 RUNBOOK - Guia Operacional

Para operações do dia a dia (Docker, Celery, troubleshooting), consulte: **[v2/docs/RUNBOOK.md](v2/docs/RUNBOOK.md)**

Tópicos cobertos:
- ✅ **Recarregar variáveis de ambiente** (`.env`) corretamente
- ✅ **Operações Celery** (worker/beat: subir, parar, logs)
- ✅ **Health checks** e validações
- ✅ **Troubleshooting** comum (Redis, containers, etc.)
- ✅ **Portas HOST vs CONTAINER** (5432/5434, 6379/6380, 8000/8002)
- ✅ **Cheat sheet** de comandos rápidos

### 🧪 Testing Policy

Para políticas e práticas de testes (RBAC, Celery flags, OAuth fixtures, paths), consulte: **[v2/docs/TESTING_POLICY.md](v2/docs/TESTING_POLICY.md)**

Baseline CI: **809 passed, 27 skipped, 6 warnings**

### 📊 GCal Dashboard

**Rota**: `/dashboard/gcal`
**Permissões**: Grupos "Controle" ou "Superintendência" (ou superuser)

Dashboard de monitoramento da sincronização com Google Calendar:
- **4 Cards de Contagem**: Status de publicação (NONE/PENDING/PUBLISHED/ERROR)
- **Filtros**: Período (date range) e status
- **Tabela Paginada**: Lista de eventos com ordenação e filtros
- **Alertas de Erros**: Top 5 erros recentes

**Endpoints Backend**:
- `GET /api/gcal/dashboard/metrics/?start=&end=` - Métricas + erros recentes
- `GET /api/gcal/dashboard/events/?status=&start=&end=&page=&page_size=` - Lista paginada

**Testes**: 12/12 passando em `v2/backend/apps/core/tests/test_gcal_dashboard_metrics.py`

## Legado (v1)

O material arquivado tem README próprio em `archive/v1_legado/README.md`.
Não execute scripts ou compose fora de `v2/`.

Desenvolvido por Matheus Norjosa
