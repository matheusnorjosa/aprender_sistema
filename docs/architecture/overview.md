# Visão Geral da Arquitetura

## Diagrama de Alto Nível

```
┌─────────────────────────────────────────────────────────────┐
│                        Frontend                              │
│                   React + Vite + Ant Design                  │
│                      (porta 5173)                            │
└─────────────────────────┬───────────────────────────────────┘
                          │ HTTP/REST
                          ▼
┌─────────────────────────────────────────────────────────────┐
│                        Backend                               │
│                  Django + DRF + Celery                       │
│                      (porta 8002)                            │
├─────────────────────────┬───────────────────────────────────┤
│         API REST        │         Background Tasks           │
│      (DRF ViewSets)     │      (Celery Workers)             │
└─────────────────────────┴───────────────────────────────────┘
          │                              │
          ▼                              ▼
┌─────────────────┐          ┌─────────────────┐
│   PostgreSQL    │          │      Redis      │
│   (porta 5434)  │          │   (porta 6380)  │
│   Dados         │          │  Cache/Filas/   │
│                 │          │  Sessões        │
└─────────────────┘          └─────────────────┘
```

> As portas do diagrama são as **publicadas no host em DEV** (`DB_HOST_PORT=5434`,
> `REDIS_HOST_PORT=6380`, `BACKEND_HOST_PORT=8002`, `FRONTEND_HOST_PORT=5173`).
> Dentro da rede do compose os serviços continuam em 5432/6379/8000.

## Componentes Principais

### Backend (`v2/backend/`)

- **Django 5.2 LTS**: Framework web principal
- **DRF**: API REST
- **Celery**: Tarefas assíncronas (sync GCal, imports assíncronos, backup agendado)
- **PostgreSQL**: Banco de dados relacional
- **Redis**: Cache, sessões (`SESSION_ENGINE=cache`) e broker do Celery

> O pipeline ETL legado (`apps.dat_ingest`) foi **removido** (#967/#971). Importação
> hoje é o pipeline export-contract — ver [ETL e Importação](../guides/etl.md).

### Frontend (`v2/frontend/`)

- **React 18**: Biblioteca UI
- **Vite**: Build tool
- **Ant Design**: Componentes UI
- **Tailwind CSS**: Utilitários CSS

### Infraestrutura (`v2/infra/`)

- **Docker Compose**: Orquestração de containers
- **Nginx**: Proxy reverso (produção)

## Estrutura de Diretórios

```
v2/
├── backend/
│   ├── apps/
│   │   ├── core/          # App principal
│   │   │   ├── models/      # Modelos Django
│   │   │   ├── serializers/ # DRF Serializers
│   │   │   ├── views/       # ViewSets DRF
│   │   │   ├── services/    # Lógica de negócio
│   │   │   ├── rbac/        # Capabilities, policies, matrix.py (SSOT executável)
│   │   │   ├── imports/     # Pipeline export-contract (hashing, normalização)
│   │   │   └── tests/       # Testes
│   │   └── dev_tools/     # Seeds (desabilitado em prod)
│   ├── config/            # Configurações Django
│   └── manage.py
├── frontend/
│   ├── src/
│   │   ├── pages/         # Páginas React
│   │   ├── components/    # Componentes
│   │   ├── api/           # Chamadas API
│   │   ├── contexts/      # Providers (auth, permissões)
│   │   └── hooks/         # React hooks
│   └── vite.config.ts
└── infra/
    ├── docker-compose.yml       # base (dev + staging)
    ├── docker-compose.override.yml  # dev
    └── docker-compose.prod.yml      # produção (usado sozinho)
```

## Fluxo de Dados

1. **Usuário** interage com o **Frontend**
2. **Frontend** faz chamadas REST ao **Backend**
3. **Backend** processa e persiste no **PostgreSQL**
4. **Celery** executa tarefas assíncronas (GCal sync)
5. **Redis** gerencia cache e filas de mensagens
