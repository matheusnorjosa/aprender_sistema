# Aprender Sistema — Plataforma v2

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
make up            # sobe o stack as_v2
make readyz        # health check
make down          # derruba os containers
```

Compose oficial: `v2/infra/docker-compose.yml` com
`COMPOSE_PROJECT_NAME=as_v2`. O script `make ban-v1` remove quaisquer
containers/redes/volumes antigos com o label `aprendersistema`.

## Legado (v1)

O material arquivado tem README próprio em `archive/v1_legado/README.md`.
Não execute scripts ou compose fora de `v2/`.
