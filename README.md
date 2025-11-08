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

## Legado (v1)

O material arquivado tem README próprio em `archive/v1_legado/README.md`.
Não execute scripts ou compose fora de `v2/`.

Desenvolvido por Matheus Norjosa
