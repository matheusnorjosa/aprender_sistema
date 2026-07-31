# Cláusulas Pétreas (CP)

Regras imutáveis do sistema que não podem ser alteradas.

!!! info "SSOT técnica"
    O contrato detalhado — qual arquivo faz cumprir cada CP, o que é convenção sem gate de CI,
    e as divergências vivas entre a cláusula e o código — está em
    [`v2/docs/specs/domain/clausulas-petreas.spec.md`](https://github.com/matheusnorjosa/aprender_sistema/blob/main/v2/docs/specs/domain/clausulas-petreas.spec.md).
    Esta página é o resumo legível. Em caso de conflito, a spec vence.

## CP-01: REQUIRE_DOCKER=1

- **v2 DEVE rodar APENAS em Docker**
- Validação obrigatória em `config/settings.py`
- v1 pode rodar local (legacy), mas v2 = Docker obrigatório

## CP-02: Política de Aprovação Manual

Ver [Política de Aprovação (PA)](politica-aprovacao.md).

- Sem auto-aprovação para fluxo SUPER
- Aprovam: superuser, **Gerente da Superintendência** ou **Assistente Administrativo do
  Controle** (PA-02). DAT e Controle puro não aprovam
- Integrações só executam após aprovação

!!! danger "Cláusula não cumprida hoje (P0 · #1610)"
    A **imutabilidade** desta autoridade não existe: o import de usuários permite que um
    membro do grupo DAT conceda a si próprio `Gerente` + `Superintendência` e passe a aprovar.
    Detalhe em [PA-02](politica-aprovacao.md#pa-02-perfil-exigido).

## CP-03: Regras de Disponibilidade

Ver [Regras de Disponibilidade (RD)](regras-disponibilidade.md).

- Não-sobreposição de eventos
- Bloqueios totais (T) e parciais (P)
- Buffer de deslocamento (D)
- Capacidade diária (M)

## CP-04: Workflow de Sub-Agents

Ordem obrigatória para agentes autônomos:

1. **Entender** → Ler código, docs, issues
2. **Planejar** → Escrever plano passo a passo
3. **Implementar** → PRs pequenos e atômicos
4. **Testar** → Testes unitários/integração/E2E
5. **Infra** → Docker/CI/CD
6. **ETL** → Importação de dados
7. **UI/UX** → Templates/views

## CP-05: Nunca Tocar v1 Sem Aprovação

- v1 está congelado (tag: `v1-freeze`)
- Mudanças exigem branch específico e aprovação

## CP-06: Padrões de Commit e PR

**Commits**: `<type>(<scope>): <message>`

- Types: `feat`, `fix`, `chore`, `docs`, `test`, `refactor`

**Branches**: `<type>/<nome>`

**PRs**: Require 1+ approval, CI verde

## CP-07: Nunca Push Direto na main

- **Push direto na `main` é proibido** — sempre via branch + Pull Request
- Merge por **squash-merge** após CI verde
- Enforced por hook local `PreToolUse` (`.claude/settings.json`) que bloqueia `git push origin main`
- ⚠️ O hook vive em `.claude/` (gitignored) → enforcement local não é herdado por um clone novo; o backstop real é o **ruleset de branch protection** da `main` no GitHub (PR obrigatório)

## CP-08: dev_tools Desabilitado em Produção

- **`apps.dev_tools` (seeds/backfills/cleanup) NÃO deve rodar em produção**
- Mecanismo: `config/settings.py:126` inclui `apps.dev_tools` apenas se `INCLUDE_DEV_TOOLS != "false"`
- **Default é `true`** (conveniência de dev), mas desde o #1466 há guard rígido em
  `config/settings.py:137-143`: quando `ENVIRONMENT == "production"`, `INCLUDE_DEV_TOOLS` é
  forçado a `False` **independentemente** da env var. Pedir `true` em produção emite warning e
  é ignorado — omitir a variável no `stack.env` deixou de violar a CP-08
- ⚠️ O guard casa `ENVIRONMENT` com a string exata `"production"`; um ambiente rotulado de
  outra forma volta a herdar o default `true`
