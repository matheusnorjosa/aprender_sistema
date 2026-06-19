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
│   (porta 5433)  │          │   (porta 6379)  │
│   Dados         │          │   Cache/Filas   │
└─────────────────┘          └─────────────────┘
```

## Componentes Principais

### Backend (`v2/backend/`)

- **Django 5.2 LTS**: Framework web principal
- **DRF**: API REST
- **Celery**: Tarefas assíncronas (sync GCal, ETL)
- **PostgreSQL**: Banco de dados relacional
- **Redis**: Cache e broker de mensagens

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
│   │   │   ├── models/    # Modelos Django
│   │   │   ├── views/     # ViewSets DRF
│   │   │   ├── services/  # Lógica de negócio
│   │   │   └── tests/     # Testes
│   │   └── dev_tools/     # Seeds (desabilitado em prod)
│   ├── config/            # Configurações Django
│   └── manage.py
├── frontend/
│   ├── src/
│   │   ├── pages/         # Páginas React
│   │   ├── components/    # Componentes
│   │   ├── api/           # Chamadas API
│   │   └── hooks/         # React hooks
│   └── vite.config.js
└── infra/
    └── docker-compose.yml
```

## Fluxo de Dados

1. **Usuário** interage com o **Frontend**
2. **Frontend** faz chamadas REST ao **Backend**
3. **Backend** processa e persiste no **PostgreSQL**
4. **Celery** executa tarefas assíncronas (GCal sync)
5. **Redis** gerencia cache e filas de mensagens
