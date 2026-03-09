# Classificacao Publico x Privado (2026-03-09)

## Escopo da auditoria

- Repositorio analisado: `aprender_sistema`
- Arquivos versionados analisados: `891`
- Metodo:
  - inventario via `git ls-files`;
  - varredura de padroes de segredo/infra (`SECRET_KEY`, `DB_PASSWORD`, tokens, blocos de chave privada, IPs de infra);
  - classificacao final por risco de exposicao em repositorio publico.

Resumo automatizado inicial:
- `publico`: 846
- `sanitizar`: 42
- `nao_publicar`: 3

## Regra de classificacao

- `publico`: pode permanecer versionado em repositorio publico.
- `sanitizar`: pode ficar publico, mas com placeholders e sem dados sensiveis/infra real.
- `nao_publicar`: nao deve permanecer versionado (usar arquivo local ignorado + template `.example`).

## Resultado final e encaixe aplicado

## 1) Nao publicar

Arquivos removidos do versionamento (mantidos localmente):

- `v2/infra/.env.dev`
- `v2/infra/.env.staging`
- `v2/infra/.env.production`

Motivo:
- sao arquivos `.env` operacionais; mesmo com placeholders, acumulam contexto de ambiente e podem receber segredo real por engano.

Substituicao versionada (templates publicos):
- `v2/infra/.env.dev.example`
- `v2/infra/.env.staging.example`
- `v2/infra/.env.production.example`

## 2) Sanitizar (publico com placeholders)

Ajustes realizados:

- `v2/docs/RUNBOOK.md`
  - removida referencia explicita de IP publico fixo (`<PUBLIC_IP>`).
- `v2/docs/DEPLOY_CHECKLIST.md`
  - removidas referencias explicitas de IP publico fixo (`<PUBLIC_IP>`).
- `v2/OAUTH_ENV_VARIABLES.md`
  - removidos exemplos com formato de client secret realista (`GOCSPX-*`);
  - substituido por placeholders (`<oauth-client-id>`, `<oauth-client-secret>`).
- `v2/infra/README.md`
  - removidos IPs internos fixos da arquitetura;
  - variaveis de host ajustadas para placeholders genericos;
  - templates referenciados atualizados para `.env.*.example`.

## 3) Publico

Permanecem publicos:

- codigo fonte backend/frontend;
- testes e CI/CD (com uso de `secrets.*` do GitHub Actions);
- documentacao tecnica sem dados reais;
- arquivos `.env.example` com placeholders.

## Regras de protecao aplicadas

Em `v2/.gitignore`:
- removido unignore de `.env.dev/.env.staging/.env.production`;
- adicionado suporte a templates `!.env.*.example`.

Em `.gitignore` (raiz, ajuste anterior):
- bloqueio para `v2/docs/private/`, `*.local.md`, `*.private.md`;
- bloqueio para reports locais de seguranca (`*-local-report*.json`);
- bloqueio para `tmp/` e `v2/tmp/`.

## Pendencias recomendadas (proxima iteracao)

1. Revisar docs antigas em `v2/docs/_archive/` para remover referencias desnecessarias a topologia real.
2. Definir politica de publicacao para `v2/infra/README.md`:
   - versao publica (sanitizada), e
   - versao privada em `v2/docs/private/infra/`.
3. Adicionar check CI para bloquear commit de `.env` nao-example.

## Checklist de validacao

- [x] arquivos `.env` operacionais removidos do versionamento
- [x] templates `.example` criados
- [x] docs operacionais sensiveis sanitizadas
- [x] regras de ignore compatibilizadas com repositorio publico
