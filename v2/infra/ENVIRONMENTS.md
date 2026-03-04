# Matriz de Ambientes (dev/staging/producao)

Fonte operacional oficial para evitar confusao de contexto no fluxo solo.

## 1) Regras Gerais

1. Sempre explicitar ambiente alvo antes de executar comandos.
2. `dev`, `staging` e `producao` usam env-file, projeto compose e comando diferentes.
3. Em staging/producao, operar com imagem publicada e identificada por tag.
4. Este documento complementa: `.codex/docs/plans/2026-03-04_ambientes-dev-staging-producao.md`.

## 2) Matriz Rapida

| Ambiente | Objetivo | Compose | Env file | Projeto compose | Porta backend |
|---|---|---|---|---|---|
| dev | Desenvolvimento local | `docker-compose.yml + docker-compose.override.yml` | `.env.dev` | `aprender_dev` | `8002` |
| staging | Homologacao | `docker-compose.yml` | `.env.staging` | `aprender_staging` | `8002` |
| producao | Runtime final | `docker-compose.prod.yml` | `.env.production` | `aprender_prod` | `8000` |

## 3) Comandos Oficiais

Usar os alvos do `v2/infra/Makefile`:

```bash
cd v2/infra

# DEV
make check-env-dev
make up-dev
make health-dev
make down-dev

# STAGING
make check-env-staging
make up-staging
make health-staging
make down-staging

# PRODUCAO (validacao local controlada)
make check-env-prod
make up-prod
make health-prod
make down-prod
```

## 4) Boas Praticas Operacionais

1. Antes de subir ambiente, rode `check-env-*`.
2. Depois de subir, valide com `health-*`.
3. Nunca assumir ambiente pelo terminal; validar pelo comando executado.
4. Para deploy real em VM, registrar `IMAGE_TAG` usada como evidencia.
5. Arquivos `.env.*` deste diretorio sao templates e nao devem conter segredos reais.

## 5) Evidencias Minimas por Mudanca

1. Comando executado e ambiente alvo.
2. Resultado de `check-env-*`.
3. Resultado de `health-*`.
4. Tag/digest da imagem (staging/producao).
