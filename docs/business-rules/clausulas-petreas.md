# Cláusulas Pétreas (CP)

Regras imutáveis do sistema que não podem ser alteradas.

## CP-01: REQUIRE_DOCKER=1

- **v2 DEVE rodar APENAS em Docker**
- Validação obrigatória em `config/settings.py`
- v1 pode rodar local (legacy), mas v2 = Docker obrigatório

## CP-02: Política de Aprovação Manual

Ver [Política de Aprovação (PA)](politica-aprovacao.md).

- Sem auto-aprovação para fluxo SUPER
- Apenas Superintendência pode aprovar
- Integrações só executam após aprovação

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
