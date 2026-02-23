# Plano de Execução — Hardening de CI/Security e Governança de Checks (2026-02-23)

**Data**: 2026-02-23  
**Base**: análise dos workflows + evidência real em GitHub Actions (run `22317756056`)  
**Objetivo**: eliminar falso verde em segurança/qualidade e garantir bloqueio real de merge no `main`.

---

## 1) Contexto validado

- **Ambiente operacional**: projeto em Docker ativo (`web`, `frontend`, `db`, `redis`, `worker`, `beat` saudáveis) via `v2/infra/docker-compose.yml`.
- **Problemas críticos confirmados**:
  - `security-scan.yml` com permissividade indevida (`continue-on-error` em checks críticos e uso de `|| true`).
  - Trivy com `exit-code: 0` (não bloqueia CVE alta/crítica).
  - Ruleset do `main` exigindo apenas `tests` e `build/lint do frontend`.
  - `security-scan` em PR condicionado por `paths: v2/**`, não validando mudança no próprio workflow em PR.
- **Riscos médios confirmados**:
  - `lighthouse CI` é informativo (ok), mas política de checks obrigatórios precisa estar explícita no ruleset.
  - `STRICT_SECURITY_HEADERS=0` em PR evita falso positivo (ok), mas falta job dedicado para validação estrita em staging/prod.
- **Riscos baixos (sem falso positivo crítico imediato)**:
  - `ci.yaml` e `docs.yml` sem permissividade indevida relevante.
  - `release.yaml` com passos de deploy placeholder (`echo`) pode gerar percepção falsa de deploy concluído.

---

## 2) Estratégia de correção (por frente)

### Frente A — Hardening do `security-scan.yml`

Issue: **#627**

Escopo:
- Remover `continue-on-error` de checks críticos (`Safety`, `pip-audit`, `Bandit`, `npm audit`, `Gitleaks`, `TruffleHog`).
- Ajustar Trivy para **falhar** em CVEs altas/críticas.
- Garantir permissões corretas para leitura de PR em secret scanning (`pull-requests: read`), eliminando erro 403 por configuração de token.
- Garantir que mudanças no workflow de segurança sejam testadas no PR (ajuste de trigger `pull_request`).

Critério de aceite:
- Vulnerabilidade/secret real faz job falhar.
- PR com alteração em `.github/workflows/security-scan.yml` dispara o workflow em `pull_request`.

Validação:
- PR de teste com falha intencional em scanner de segurança deve bloquear merge.

---

### Frente B — Governança de checks obrigatórios no `main` (ruleset)

Issue: **#628**

Escopo:
- Atualizar ruleset `Protect main` para refletir gates reais de qualidade/segurança.
- Tornar explícito que `lighthouse CI` é informativo (não obrigatório).

Checks obrigatórios propostos:
- `tests`
- `lint`
- `build/lint do frontend`
- `checklist tests (meta, a11y, security)`
- `Python Dependencies`
- `Frontend Dependencies`
- `Container Scan`
- `Secret Detection`

Critério de aceite:
- PR sem esses checks verdes não pode ser mergeado no `main`.

Validação:
- Simular falha em um check obrigatório e confirmar bloqueio por ruleset.

---

### Frente C — Segurança estrita de headers em ambiente real (staging/prod)

Issue: **#629**

Escopo:
- Criar workflow/job dedicado para `security-headers.spec.ts` com `STRICT_SECURITY_HEADERS=1` contra URL real de staging/prod.
- Manter PR checklist não-estrito para evitar falso positivo de ambiente efêmero.

Critério de aceite:
- Execução dedicada (manual/schedule) falha quando headers mandatórios não estão corretos em ambiente real.

Validação:
- Rodar workflow apontando para staging e confirmar comportamento.

---

### Frente D — Release workflow: remover falso sinal de deploy (placeholder)

Issue: **#630**

Escopo:
- Substituir passos de deploy placeholder por:
  - gate explícito de "não implementado" (falha) **ou**
  - integração real de deploy com evidência.

Critério de aceite:
- Workflow não comunica deploy concluído sem execução real.

Validação:
- `workflow_dispatch` deve produzir status coerente com deploy real.

---

## 3) Ordem de execução (issues)

1. **#627** Hardening `security-scan.yml` + trigger de PR para workflow file.
2. **#628** Ruleset `main` com checks obrigatórios alinhados.
3. **#629** Job dedicado de headers estritos em staging/prod.
4. **#630** Correção do `release.yaml` para eliminar falso sinal de deploy.

---

## 4) Dependências e observações

- A frente **B** depende de nomes de checks estáveis após a frente **A**.
- A frente **C** depende de URL/segredo/variável de ambiente de staging/prod (`BASE_URL` ou equivalente).
- O ciclo será executado no processo oficial: **issue -> branch -> PR -> CI verde -> merge**.

---

## 5) Referências

- Epic atual: `#620`
- Issues deste ciclo: `#627`, `#628`, `#629`, `#630`
- Workflow alvo: `.github/workflows/security-scan.yml`
- Workflow alvo: `.github/workflows/frontend-ci.yml`
- Workflow alvo: `.github/workflows/release.yaml`
- Ruleset alvo: `Protect main` (`id: 9793909`)
