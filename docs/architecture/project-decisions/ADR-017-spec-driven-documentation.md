# ADR-017: Documentação Spec-Driven (SDD)

**Status:** Accepted
**Date:** 2026-06-19
**Decider:** Matheus Norjosa

## Context

O acervo de documentação chegou a ~326 arquivos `.md` (210 versionados + 116 locais) sem sinalização de
canonicidade: 21 docs `stale` (ensinavam comportamento que não existe mais — ex.: 21 comandos ETL do
`apps.dat_ingest` removido), contagens divergentes (setores/funções/models transcritas à mão e desatualizadas)
e dezenas de links quebrados. Ler um doc não dizia **se ele é verdade hoje**, **qual código é a fonte**, nem
**quando foi verificado**.

Agravante: contratos críticos (CP-07 "nunca push na main", CP-08 "dev_tools off em prod") viviam só em
`.claude/CLAUDE.md` — um arquivo **local**, que não existe num clone limpo. Qualquer regra que dependesse de
`.claude/` ou `.agents/` quebrava fora da máquina do dev.

## Decision

Adotar **Spec-Driven Development (SDD)** para a documentação, com uma camada de specs vivas versionada em
[`v2/docs/specs/`](https://github.com/matheusnorjosa/aprender_sistema/blob/main/v2/docs/specs/INDEX_SDD.md):

1. **Frontmatter obrigatório** em todo doc vivo (`specs/`, `runbooks/`, `reference/`, `decisions/`): `status`
   (`canonical|active|draft|stale|historical`), `last_verified` (data da última checagem contra o código) e
   `sources_of_truth` (arquivos de código que a spec descreve). Sem frontmatter ⇒ tratar como histórico.
2. **Uma verdade por tópico.** Um SSOT por domínio; os demais docs **linkam**, não duplicam (evita drift de
   contagens). A spec é um contrato conciso que aponta para o guia detalhado + o código.
3. **Spec = contrato vivo, código = implementação.** Toda spec lista `sources_of_truth` reais e verificados.
4. **Gerar em vez de copiar.** Tabelas derivadas do código (setores/funções, capability×grupo) são geradas
   (`python manage.py rbac_matrix_doc`), não transcritas.
5. **Histórico é imutável e isolado.** `_archive/`, `analysis/`, planos concluídos e relatórios datados ficam
   fora da navegação viva e **não se "corrigem"**.
6. **Nada crítico fora do git.** Os contratos *enforced* (CP-01..08, RD-01..08, PA-01..07, RF) passam a viver em
   docs versionados: `docs/business-rules/clausulas-petreas.md` (CP-07/CP-08 já promovidos) + as specs em
   [`specs/domain/`](https://github.com/matheusnorjosa/aprender_sistema/blob/main/v2/docs/specs/domain/).

### Decisão sobre `CLAUDE.md` / `AGENTS.md` / `.claude/`

Mantidos **local-only** (gitignored) **de forma intencional**. Como os contratos agora estão em git (item 6),
**nenhum comportamento crítico depende de `.claude/` num clone limpo** — esses arquivos são *tooling* de
conveniência do dev (instruções de agente, skills locais), não fonte de verdade. Não versionar evita ruído e
vazamento de configuração local. Critério de conclusão "decisão explícita sobre CLAUDE.md/AGENTS.md" do plano
SDD: **satisfeito por esta ADR** (local-only documentado).

## Consequences

- Todo módulo vivo (backend/frontend/infra) e contrato (domain) ganha uma `*.spec.md` com `status` +
  `last_verified` + `sources_of_truth`.
- **Proibido**: documento vivo sem frontmatter; transcrever tabelas que o código gera; "corrigir" arquivos em
  `_archive/`; mover arquivo sem corrigir os links no mesmo commit.
- **Gate de CI** (Fase 6) passa a barrar links relativos quebrados em docs canonical/active e frontmatter
  ausente — impedindo regressão.
- Specs novas em `v2/docs/specs/` **não** entram na nav do MkDocs (que publica só `docs/`); são referência
  interna versionada. Links de páginas MkDocs para `v2/docs/*` usam URL absoluta (`blob/main`), pois caminho
  relativo cross-tree quebra `mkdocs build --strict`.

## References

- Plano: `v2/docs/plans/PLAN_sdd_migration_2026-06-19.md`
- Auditoria: `v2/docs/reports/AUDITORIA_DOCUMENTAL_2026-06-19.md`
- Índice de specs: `v2/docs/specs/INDEX_SDD.md`
- Contratos: `docs/business-rules/clausulas-petreas.md` (CP-01..08)
- [ADR-010](ADR-010-deploy-portainer-direct-to-prod.md) (deploy), [ADR-012](ADR-012-dependency-guardrails.md) (guardrails)
