# Plano: Type Hints 100% Coverage

**Data**: 2026-01-09
**Status**: Planejado
**Meta**: 100% type hints em código de produção

---

## 1. Estado Atual

### Coverage por Módulo

| Módulo | Total | Tipado | % | Status |
|--------|-------|--------|---|--------|
| config/ | 6 | 6 | **100%** | ✅ Perfeito |
| core/models/ | 20 | 19 | **95%** | ✅ Excelente |
| core/serializers/ | 12 | 11 | **92%** | ✅ Excelente |
| core/views/ | 9 | 8 | **89%** | ✅ Excelente |
| core/services/ | 23 | 18 | **78%** | ⚠️ Gap |
| core/ (root) | 35 | 31 | **89%** | ✅ Bom |
| core/commands/ | 3 | 2 | **67%** | ✅ Bom |
| dat_ingest/ | 68 | 21 | **31%** | 🔷 Excluído |
| dev_tools/ | 22 | 10 | **45%** | 🔷 Dev-only |

**Resumo**: 68% em escopo de produção (core + config)

---

## 2. Estratégia de Priorização

### Tier 1: CRÍTICO (Produção)
Arquivos no path crítico da aplicação.

### Tier 2: IMPORTANTE (Produção secundária)
Arquivos de configuração e utilitários.

### Tier 3: DESEJÁVEL (Dev/ETL)
Comandos de desenvolvimento e ETL.

### Tier 4: OPCIONAL (Testes)
Arquivos de teste (baixo ROI).

---

## 3. Plano de Execução

### Fase 1: Core Services (Semana 1-2)
**Meta**: core/services/ de 78% → 100%

| PR | Arquivo | LOC | Complexidade | Esforço |
|----|---------|-----|--------------|---------|
| #342 | `normalize.py` | 410 | Média | 8h |
| #343 | `resolvers.py` | 285 | Média | 6h |
| #344 | `project_normalizer.py` | 140 | Média | 4h |
| #345 | `gcal_sync_service.py` | 63 | Simples | 2h |
| #346 | `services/__init__.py` | 1 | Trivial | 0.5h |

**Total Fase 1**: ~20h | 5 PRs

---

### Fase 2: Core Root (Semana 2-3)
**Meta**: core/ (root) de 89% → 100%

| PR | Arquivo | LOC | Complexidade | Esforço |
|----|---------|-----|--------------|---------|
| #347 | `urls.py` | 273 | Média | 6h |
| #348 | `auth_backends.py` | 80 | Simples | 2h |
| #349 | `admin_site.py` | 44 | Simples | 1h |
| #350 | `views.py` (root) | 61 | Simples | 1h |
| #351 | `__init__.py` files (5) | 5 | Trivial | 0.5h |

**Total Fase 2**: ~10h | 5 PRs

---

### Fase 3: Core Models/Views/Serializers (Semana 3)
**Meta**: Completar 100% nos módulos principais

| PR | Arquivo | LOC | Complexidade | Esforço |
|----|---------|-----|--------------|---------|
| #352 | `models/__init__.py` | 1 | Trivial | 0.5h |
| #353 | `serializers/__init__.py` | 1 | Trivial | 0.5h |
| #354 | `views/__init__.py` | 1 | Trivial | 0.5h |
| #355 | `commands/__init__.py` | 1 | Trivial | 0.5h |

**Total Fase 3**: ~2h | 4 PRs

---

### Fase 4: Dev Tools (Semana 4)
**Meta**: dev_tools/ de 45% → 100%

| PR | Arquivo | LOC | Complexidade | Esforço |
|----|---------|-----|--------------|---------|
| #356 | `seed_e2e_users.py` | 187 | Simples | 3h |
| #357 | `seed_rbac.py` | 156 | Simples | 3h |
| #358 | `seed_gerencias.py` | 107 | Simples | 2h |
| #359 | `seed_gerentes.py` | 354 | Média | 5h |
| #360 | `seed_produtos.py` | 138 | Simples | 2h |
| #361 | `seed_tipos_evento.py` | 79 | Simples | 1h |
| #362 | `seed_projetos_fluxo_*.py` (2) | 230 | Média | 4h |
| #363 | `cleanup_e2e_data.py` | 194 | Simples | 3h |
| #364 | `backfill_is_online.py` | 132 | Simples | 2h |
| #365 | `fix_projetos_gerencia.py` | 181 | Simples | 3h |
| #366 | `migrate_rbac_groups.py` | 162 | Simples | 2h |
| #367 | `link_projetos_gerencias.py` | 135 | Simples | 2h |
| #368 | `populate_municipio_coords.py` | 163 | Simples | 2h |
| #369 | Arquivos `__init__.py` (4) | 4 | Trivial | 0.5h |

**Total Fase 4**: ~35h | 14 PRs

---

### Fase 5: DAT Ingest - Services (Semana 5-6)
**Meta**: dat_ingest/services/ tipado

| PR | Arquivo | LOC | Complexidade | Esforço |
|----|---------|-----|--------------|---------|
| #370 | `loaders.py` | 437 | Alta | 10h |
| #371 | `processors.py` | ~300 | Alta | 8h |
| #372 | `normalizers.py` | ~300 | Média | 6h |
| #373 | `parse_acompanhamento.py` | ~200 | Média | 5h |
| #374 | `parse_bloqueios.py` | ~200 | Simples | 4h |
| #375 | `acompanhamento_normalize.py` | ~150 | Simples | 3h |
| #376 | `resolvers.py` (dat_ingest) | ~100 | Simples | 2h |

**Total Fase 5**: ~38h | 7 PRs

---

### Fase 6: DAT Ingest - Commands (Semana 6-7)
**Meta**: dat_ingest/management/commands/ tipado

| PR | Arquivo | LOC | Complexidade | Esforço |
|----|---------|-----|--------------|---------|
| #377 | `etl_all.py` | ~100 | Simples | 2h |
| #378 | `etl_upsert_acompanhamento.py` | ~200 | Média | 4h |
| #379 | `etl_upsert_core.py` | ~150 | Média | 3h |
| #380 | `etl_import_dat_cadastros.py` | ~150 | Média | 3h |
| #381 | `etl_import_acoes_controle.py` | ~150 | Média | 3h |
| #382 | `etl_load_xlsx.py` | ~100 | Simples | 2h |
| #383 | `etl_upsert_deslocamento.py` | ~100 | Simples | 2h |
| #384 | `benchmark_etl.py` | ~50 | Simples | 1h |
| #385 | Outros commands (8) | ~800 | Média | 12h |

**Total Fase 6**: ~32h | 9 PRs

---

### Fase 7: DAT Ingest - Misc (Semana 7)
**Meta**: Completar dat_ingest/

| PR | Arquivo | LOC | Complexidade | Esforço |
|----|---------|-----|--------------|---------|
| #386 | `constants.py` | ~50 | Trivial | 1h |
| #387 | `apps.py`, `admin.py` | ~20 | Trivial | 0.5h |
| #388 | `urls.py` | ~30 | Trivial | 0.5h |
| #389 | `views.py` | ~100 | Simples | 2h |
| #390 | `__init__.py` files | ~5 | Trivial | 0.5h |

**Total Fase 7**: ~5h | 5 PRs

---

### Fase 8: Testes - Core (Semana 8)
**Meta**: Tipar testes críticos (opcional)

| PR | Escopo | Arquivos | Esforço |
|----|--------|----------|---------|
| #391 | `core/tests/test_models_*.py` | ~20 | 10h |
| #392 | `core/tests/test_views_*.py` | ~15 | 8h |
| #393 | `core/tests/test_services_*.py` | ~10 | 5h |
| #394 | `core/tests/test_serializers_*.py` | ~10 | 5h |

**Total Fase 8**: ~28h | 4 PRs

---

### Fase 9: Testes - ETL/Dev (Semana 9)
**Meta**: Tipar testes restantes (opcional)

| PR | Escopo | Arquivos | Esforço |
|----|--------|----------|---------|
| #395 | `dat_ingest/tests/` | ~23 | 15h |
| #396 | `dev_tools/tests/` | ~3 | 2h |

**Total Fase 9**: ~17h | 2 PRs

---

## 4. Resumo de Esforço

| Fase | Escopo | Arquivos | Horas | PRs |
|------|--------|----------|-------|-----|
| 1 | core/services/ | 5 | 20h | 5 |
| 2 | core/ (root) | 5 | 10h | 5 |
| 3 | core/models,views,serializers | 4 | 2h | 4 |
| 4 | dev_tools/ | 14 | 35h | 14 |
| 5 | dat_ingest/services/ | 7 | 38h | 7 |
| 6 | dat_ingest/commands/ | 9 | 32h | 9 |
| 7 | dat_ingest/misc | 5 | 5h | 5 |
| 8 | core/tests/ | 4 | 28h | 4 |
| 9 | dat_ingest,dev_tools/tests/ | 2 | 17h | 2 |
| **TOTAL** | | **55** | **187h** | **55** |

---

## 5. Cronograma

```
Semana 1-2:  Fase 1 (core/services/) ........... 20h
Semana 2-3:  Fase 2 (core/ root) ............... 10h
Semana 3:    Fase 3 (__init__.py files) ........ 2h
Semana 4:    Fase 4 (dev_tools/) ............... 35h
Semana 5-6:  Fase 5 (dat_ingest/services/) ..... 38h
Semana 6-7:  Fase 6 (dat_ingest/commands/) ..... 32h
Semana 7:    Fase 7 (dat_ingest/misc) .......... 5h
Semana 8:    Fase 8 (core/tests/) .............. 28h [opcional]
Semana 9:    Fase 9 (tests restantes) .......... 17h [opcional]
```

**Timeline**: 7 semanas (código) + 2 semanas (testes opcionais)

---

## 6. Métricas de Sucesso

### Por Fase

| Fase | Meta Coverage |
|------|---------------|
| Após Fase 1 | core/services/ = 100% |
| Após Fase 2 | core/ = 100% |
| Após Fase 3 | core/* = 100% |
| Após Fase 4 | dev_tools/ = 100% |
| Após Fase 7 | dat_ingest/ = 100% |
| Após Fase 9 | Tudo = 100% |

### Verificação

```bash
# Rodar Pyright sem erros
cd v2/backend && pyright apps/ config/

# Verificar coverage
pyright --outputjson | jq '.generalDiagnostics | length'
# Meta: 0 erros
```

---

## 7. Padrões de Typing

### Imports Obrigatórios

```python
from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from apps.core.models import Usuario, Solicitacao
```

### Padrões Comuns

```python
# Função com Optional
def get_user(user_id: int) -> Usuario | None:
    ...

# QuerySet tipado
def get_active_users() -> QuerySet[Usuario]:
    ...

# Dict com tipos
def process_data(data: dict[str, Any]) -> dict[str, str]:
    ...

# Callable
def register_handler(handler: Callable[[Request], Response]) -> None:
    ...
```

### Supressões Permitidas

```python
# Apenas quando Django/DRF não suporta typing
# pyright: reportUnknownMemberType=false  # DRF serializer.data

# NUNCA suprimir sem comentário explicativo
```

---

## 8. Checklist por PR

- [ ] Arquivo tem `from __future__ import annotations`
- [ ] Todas as funções têm return type
- [ ] Todos os parâmetros têm type hints
- [ ] Variáveis de classe têm type hints
- [ ] `pyright <arquivo>` passa sem erros
- [ ] Testes existentes continuam passando
- [ ] Nenhum `# type: ignore` sem justificativa

---

## 9. Configuração Pyright

### pyproject.toml atual

```toml
[tool.pyright]
include = ["apps/core", "config"]
exclude = ["**/migrations", "**/__pycache__"]
pythonVersion = "3.12"
typeCheckingMode = "strict"
```

### Expansão proposta (Fase 4+)

```toml
[tool.pyright]
include = [
    "apps/core",
    "apps/dev_tools",  # Fase 4
    "apps/dat_ingest", # Fase 5-7
    "config"
]
exclude = [
    "**/migrations",
    "**/__pycache__",
    "**/tests"  # Remover na Fase 8-9
]
```

---

## 10. Riscos e Mitigações

| Risco | Probabilidade | Impacto | Mitigação |
|-------|---------------|---------|-----------|
| Django ORM difícil de tipar | Alta | Médio | Usar django-stubs, permitir supressões documentadas |
| DRF serializers complexos | Alta | Médio | Usar djangorestframework-stubs |
| Tempo subestimado | Média | Médio | Buffer de 20% em cada fase |
| Breaking changes | Baixa | Alto | Testes devem passar antes do merge |
| Conflitos de merge | Média | Baixo | PRs pequenos, merge frequente |

---

## 11. Dependências

```
# requirements-dev.txt (já instalados)
pyright==1.1.382
django-types==0.19.1
djangorestframework-types==0.8.0
types-requests==2.32.0.20240914
types-redis==4.6.0.20240903
celery-types==0.22.0
```

---

## 12. Decisão: Fases Obrigatórias vs Opcionais

### Obrigatórias (Produção)
- ✅ Fase 1: core/services/
- ✅ Fase 2: core/ (root)
- ✅ Fase 3: __init__.py files

**Resultado**: 100% em código de produção (core + config)
**Esforço**: 32h (~4 dias)

### Recomendadas (Dev/ETL)
- 🔷 Fase 4: dev_tools/
- 🔷 Fase 5-7: dat_ingest/

**Resultado**: 100% em todo código (exceto testes)
**Esforço adicional**: 110h (~14 dias)

### Opcionais (Testes)
- ⚪ Fase 8-9: Testes

**Resultado**: 100% absoluto
**Esforço adicional**: 45h (~6 dias)

---

## Aprovação

- [ ] Aprovar Fases 1-3 (obrigatórias)
- [ ] Aprovar Fases 4-7 (recomendadas)
- [ ] Aprovar Fases 8-9 (opcionais)
- [ ] Iniciar execução

**Recomendação**: Executar Fases 1-3 imediatamente (32h) para atingir 100% em produção.
