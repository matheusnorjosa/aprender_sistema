# Constitution — princípios imutáveis

Leitura **obrigatória** antes de qualquer mudança. Toda spec, todo commit e todo PR
deve honrar isto. Se uma regra aqui conflita com uma instrução de tarefa, **esta vence**
— e você sinaliza o conflito em vez de seguir.

---

## 🛑 Hard stops (nunca faça)

1. **Nunca `git push` na `main`.** Sempre branch + PR. (Um hook bloqueia o push direto.)
2. **Nunca rode o v2 fora do Docker** — sem `python manage.py` no host (CP-01).
3. **Nunca abra PR sem o staging gate** 8/8 + evidência (`ALL 8 CHECKS PASSED`) no corpo.
4. **Nunca commite, empurre ou abra PR sem o usuário pedir.** Pare no "teste verde" e relate.
5. **Nunca** crie classes `Is<Role>` nem `user.groups.filter(name=...)` em views —
   use `HasPerm("codename")` (bloqueado por lint).
6. **Nunca** edite migration já aplicada — crie uma nova de fix.
7. **Nunca** use SQL cru — só ORM.
8. **Nunca** auto-aprove `Solicitacao` de projeto SUPER (PA-01).
9. **Nunca** inclua trailer "Claude Code"/"Co-Authored-By" em commit.
10. **Nunca** declare algo pronto sem rodar e ver o verde.

---

## ⚖️ Cláusulas Pétreas (CP-01..08)

> **SSOT:** [`docs/business-rules/clausulas-petreas.md`](../docs/business-rules/clausulas-petreas.md).
> O resumo abaixo é para consulta rápida — em qualquer divergência, **o SSOT manda** e é lá que se corrige.

- **CP-01** Docker-only.
- **CP-02** Política de Aprovação PA-01..07; tudo em `AuditLog`.
- **CP-03** Regras de Disponibilidade RD-01..08; storage UTC, comparação em `America/Fortaleza`.
- **CP-04** Workflow: Entender → Planejar → Implementar → Testar → Infra → ETL → UI/UX.
- **CP-05** v1 congelado (`fix/v1-*` → `main-v1`).
- **CP-06** Conventional commits: `<tipo>(<escopo>): <mensagem>` minúsculo, ≤72, imperativo.
- **CP-07** Nunca push direto na `main`; PR obrigatório.
- **CP-08** `INCLUDE_DEV_TOOLS=false` em produção.

---

## 🏛️ Barras de qualidade (inegociáveis)

- **Camadas** (import-linter, ADR-012): `models` (SSOT, constraints no DB) → `services`
  (lógica + escrita, `transaction.atomic()`) → `views` (thin) / `serializers` (shape+validação).
  Views nunca escrevem direto.
- **Type-safety**: Pyright strict, type hints 100% (PEP 695). Sem `Any` sem justificativa.
  Frontend TypeScript strict.
- **RBAC**: capability via `HasPerm`. Aprovador = `is_superuser` ∨ (`Gerente`∧`Superintendência`)
  ∨ (`Assistente Administrativo`∧`Controle`). Policy pública: `access_solicitation_approvals`.
- **AuditLog** em writes críticos (APPROVE/REJECT/PUBLISH/CANCEL/UPDATE).
- **Performance**: `select_related`/`prefetch_related` em `get_queryset` (sem N+1).
- **Testes**: cobertura ≥ 85% (`--cov-fail-under=85`), ~100% no crítico. Comportamento,
  não implementação; nomes em 3ª pessoa; 403 antes de 400; `GCAL_CLIENT=fake` em CI.
- **TDD** (CP-04): teste que falha antes do código.
- **Legibilidade**: nomes específicos (`usuario_aprovador`, não `user`); early returns;
  máx. 2-3 níveis de indentação; comentário explica o *porquê*, não o *o quê*.

---

## ✅ Verification gate (antes de dizer "pronto")

- [ ] Rodei o teste/comando de fato?
- [ ] Vi a saída de sucesso (verde), não suposição?
- [ ] Verifiquei efeitos colaterais (regressão, lint, tipos)?
- [ ] Relatei fielmente — se falhou, digo que falhou, com a saída.

---

## 📌 Domínio (índice — SSOT em `docs/business-rules/`)

Referencie as regras por **código**, sempre a partir do SSOT versionado — não parafraseie
aqui (evita drift de contagem/descrição):

- **RD-01..08** (disponibilidade) → [`regras-disponibilidade.md`](../docs/business-rules/regras-disponibilidade.md)
- **PA-01..07** (aprovação) → [`politica-aprovacao.md`](../docs/business-rules/politica-aprovacao.md)
- **RF** (requisitos funcionais) → [`requisitos-funcionais.md`](../docs/business-rules/requisitos-funcionais.md)
- **CP-01..08** (cláusulas pétreas) → [`clausulas-petreas.md`](../docs/business-rules/clausulas-petreas.md)

Profundidade operacional para o Claude Code: `.claude/skills/aprender-domain/`.
