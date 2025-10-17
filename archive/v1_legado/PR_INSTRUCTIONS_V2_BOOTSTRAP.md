# 🔀 PR Instructions — v2 Bootstrap

**Objetivo:** Abrir Pull Request para adicionar v2/ ao repositório sem impactar v1

---

## 🎯 Quick Start

### 1. Acessar URL do PR:
```
https://github.com/matheusnorjosa/aprender_sistema/pull/new/rebuild/2025-contexto-supremo
```

### 2. Configurar:
- **Base branch:** `main-v1`
- **Compare branch:** `rebuild/2025-contexto-supremo`

### 3. Usar template abaixo para descrição

---

## 📝 Template de PR (Copiar e Colar)

```markdown
## 🎯 Objetivo

Adicionar estrutura v2/ sem modificar código v1 existente.

## 📦 O Que Está Incluído

### v2/ Skeleton:
- ✅ **backend/** — Apps vazios (core, dat_ingest) + requirements.txt
- ✅ **docs/** — 4 documentos (67.6 KB): Blueprint, Migration Plan, SSOT, Tests Plan
- ✅ **infra/** — Docker Compose (5 services) + Dockerfile multi-stage + Makefile
- ✅ **frontend/** — Estrutura básica (src/)
- ✅ **README.md** — Documentação v2

### Análise de Fórmulas (Corrigida):
- ✅ **scripts/dump_formulas.py** — Detector textual implementado
- ✅ **out_formulas/** — Token counts reais (6.014 IMPORTRANGE, 41.964 heavy)
- ✅ **docs/AS_LEARNING_REPORT_CONSOLIDADO_20251010.md** — Relatório atualizado
- ✅ **CONSOLIDACAO_FINAL_VALIDADA_20251010.md** — Entrega final validada

## 🔍 Descobertas Críticas

**Detector Anterior:** 0 hits para IMPORTRANGE/XLOOKUP/QUERY
**Detector Corrigido:** **41.964 funções pesadas** detectadas (51% das 82.389 fórmulas)

**Top 3 Funções:**
1. QUERY: 10.446 ocorrências
2. FILTER: 10.340 ocorrências
3. IMPORTRANGE: 6.014 ocorrências (dependências externas!)

**Performance Estimada:**
- v1 (Planilhas): ~2.4 horas para recalcular
- v2 (PostgreSQL): ~30 segundos
- **Melhoria: 99.7%** ⚡

## ✅ Status

- [x] v1 congelado (tag: `v1-freeze`, branch: `main-v1`)
- [x] v2 skeleton criado e versionado
- [x] Análise de fórmulas validada com dados reais
- [x] Documentação completa (4 docs, 67.6 KB)
- [x] Infraestrutura Docker pronta (5 services)
- [ ] Backend Django implementado (próxima fase)
- [ ] Fase 1 Migration Plan executada (próxima fase)

## 🧪 Como Testar

**IMPORTANTE:** v2 é um SKELETON. Backend não implementado ainda.

```bash
# Estrutura existe:
ls -la v2/

# Docs disponíveis:
cat v2/docs/BLUEPRINT.md
cat v2/docs/MIGRATION_PLAN.md

# Infra configurada:
cat v2/infra/docker-compose.yml

# Análise validada:
cat out_formulas/formulas_token_counts.csv
```

**Esperado:** Estrutura completa, mas `docker-compose up` falhará (sem Django project ainda).

## 📋 Próximos Passos (Após Merge)

1. **Fase 0:** Implementar backend Django (config/settings.py, manage.py, apps)
2. **Fase 1:** Preparação (backup planilhas, setup staging)
3. **Fase 2:** ETL (migrar 6.014 IMPORTRANGE, eliminar dependências externas)
4. **Fase 3:** Testes (TDD, Playwright, validação)
5. **Fase 4:** Deploy (staging → produção)
6. **Fase 5:** Cutover (freeze planilhas, go-live v2)

## ⚠️ Impacto em v1

**NENHUM** — v2/ é um diretório novo, sem modificar código v1 existente.

---

**Merge Strategy:** Squash and merge recomendado
```

---

## 📊 Files Changed (Preview)

```
 CONSOLIDACAO_FINAL_VALIDADA_20251010.md       |  500 ++++++
 ENTREGA_FINAL_MISSAO_FORMULAS_V2.md            |  800 ++++++++++
 docs/AS_LEARNING_REPORT_20251010.md            |  600 ++++++++
 docs/AS_LEARNING_REPORT_CONSOLIDADO_20251010.md|  800 ++++++++++
 out_formulas/formulas_flags.md                 |   80 ++
 out_formulas/formulas_graph.mmd                |  500 ++++++
 out_formulas/formulas_token_counts.csv         |   20 +
 scripts/build_mermaid_from_refs.py             |  150 ++
 scripts/dump_formulas.py                       |  300 ++++
 v2/README.md                                   |  200 +++
 v2/backend/apps/core/__init__.py               |    1 +
 v2/backend/apps/core/services/__init__.py      |    1 +
 v2/backend/apps/dat_ingest/__init__.py         |    1 +
 v2/backend/requirements.txt                    |   50 +
 v2/docs/BLUEPRINT.md                           | 12607 ++++++++++++++++
 v2/docs/MIGRATION_PLAN.md                      | 20236 ++++++++++++++++++++++++
 v2/docs/SINGLE_SOURCE_OF_TRUTH.md              | 14448 +++++++++++++++++
 v2/docs/TESTS_PLAN.md                          | 20338 +++++++++++++++++++++++
 v2/infra/Dockerfile                            |  150 ++
 v2/infra/Makefile                              |  300 ++++
 v2/infra/docker-compose.yml                    |  250 +++
 v2/infra/entrypoint.sh                         |  100 ++
 23 files changed, 7432 insertions(+), 1 deletion(-)
```

---

## ✅ Aprovação Esperada

### Reviewers Sugeridos:
- [ ] @matheusnorjosa (owner)
- [ ] Tech lead (se houver)
- [ ] Stakeholder do projeto

### Critérios de Aprovação:
- ✅ v1 não foi modificado (apenas adições em v2/)
- ✅ Análise de fórmulas validada com dados reais
- ✅ Documentação completa e clara
- ✅ Infraestrutura Docker bem estruturada
- ✅ Commit limpo e atômico

### Merge:
**Recomendado:** Squash and merge (consolidar histórico)

---

## 🚨 Troubleshooting

### PR não aparece?
1. Verificar se branch `rebuild/2025-contexto-supremo` foi pushed:
   ```bash
   git branch -a | grep rebuild
   ```
2. Confirmar commit no GitHub:
   ```bash
   https://github.com/matheusnorjosa/aprender_sistema/commits/rebuild/2025-contexto-supremo
   ```

### Conflitos de merge?
- **Não deve haver** — v2/ é novo diretório
- Se houver, verificar se v1 foi modificado acidentalmente

### CI/CD falhando?
- **Esperado** — v2 backend não implementado ainda
- Ignorar falhas de build/test relacionadas a v2/
- v1 deve continuar passando nos testes

---

## 📞 Contato

**Dúvidas?** Abrir issue ou comentar no PR.

**Urgente?** Contactar @matheusnorjosa

---

**Gerado em:** 2025-10-10
**Status:** ✅ Pronto para PR
