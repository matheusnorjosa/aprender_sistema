# Testing Policy — Aprender v2

Este documento consolida práticas e contratos adotados nos testes para manter o CI previsível e fiel ao domínio.

## Ambiente de CI

- **Runtime**: Python 3.12, PostgreSQL 15, Redis 7, TZ `America/Fortaleza`
- **Settings**: `DJANGO_SETTINGS_MODULE=config.settings`, `ENVIRONMENT=testing`, `REQUIRE_DOCKER=0`
- **Integrações externas**:
  - `GCAL_CLIENT=fake`, `GCAL_SEND_UPDATES=none`
- **Diretórios de import**:
  - `IMPORT_OUTPUT_DIR` e `IMPORT_DATA_DIR` resolvidos no workspace do CI
- **Paths**:
  - Nunca usar `/app` hardcoded em testes
  - Preferir `Path(settings.BASE_DIR)` para paths absolutos

## RBAC e HTTP Status (security-first)

**Contrato**: validação de permissão **antes** de parâmetros.

- **Sem permissão** → `403 Forbidden`
- **Com permissão + dados inválidos** → `400 Bad Request`
- **Com permissão + dados válidos** → `200/204`

**Em testes que validam parâmetros (esperam 400)**:
- Autentique um usuário com grupo "Controle" ou "Superintendência"
- Exemplo:
  ```python
  from django.contrib.auth.models import Group
  grupo, _ = Group.objects.get_or_create(name="Controle")
  user.groups.add(grupo)
  ```

## Celery / GCal Safety

**Flag padrão**: `FEATURE_AUTO_APPLY_ENABLED=False`

**Quando o teste precisa do caminho de aplicação/erro**:
- Use `@override_settings(FEATURE_AUTO_APPLY_ENABLED=True)` (ou fixture por teste)
- Ajuste asserts de `ERROR`/`SKIPPED` conforme a flag ativa

**Importante**:
- **Não** usar `CELERY_TASK_ALWAYS_EAGER=1` no CI — causa divergências em testes de segurança

## OAuth Fixtures (Google)

Os tokens devem ser criptografados usando a **mesma derivação do serviço**:
- `_get_fernet_key()` (usa `GCAL_ENCRYPTION_KEY` ou fallback derivado de `SECRET_KEY` fora de produção)

**Helpers nos testes**:
```python
from cryptography.fernet import Fernet
from apps.core.services.google_oauth import _get_fernet_key

def _encrypt_token_for_tests(token: str) -> bytes:
    return Fernet(_get_fernet_key()).encrypt(token.encode("utf-8"))

def _decrypt_token_for_tests(encrypted: bytes) -> str:
    return Fernet(_get_fernet_key()).decrypt(encrypted).decode("utf-8")
```

**Para rotação de chave**:
- Use `monkeypatch.setenv("GCAL_ENCRYPTION_KEY", ...)` no escopo do teste

## GCal Attendees

- O builder inclui apenas: `COORDENADOR`, `FORMADOR`, `COORD_ACOMPANHA`
- `guest_email` mantém o papel formal quando não há usuário (aparece como attendee)

## Seed / Imports / Arquivos

**Paths robustos**:
```python
from pathlib import Path
from django.conf import settings

csv_path = Path(settings.BASE_DIR) / "data/municipios_coordenadas.csv"
```

*(Corrigido em 2026-07-24: o exemplo anterior apontava para `apps/core/data/projetos_fluxo.csv`,
que **não existe** — nem o arquivo, nem o diretório `apps/core/data/`.)*

**Evitar**:
- Caminhos relativos ao CWD (quebram conforme diretório de execução)
- Hardcoded `/app` (específico de container, não funciona localmente)

**Artefatos de import**:
- Devem ser gravados sob `IMPORT_OUTPUT_DIR` ou `BASE_DIR`, nunca em `/app`.
  *(O ETL legado foi removido; o caminho atual é `import_export_contract` + endpoints DRF.)*

## Princípios

1. **Não remover nem pular testes** por conveniência
2. **Ajustar testes** quando divergirem do "Contexto Consolidado v2"
3. **Ajustar código** só quando o comportamento real estiver incorreto
4. **Fixtures idempotentes**: usar `get_or_create()` para evitar cross-poluição
5. **Security-first**: validar permissões antes de parâmetros (403 → 400 → 200)
6. **xdist-safe** (ADR-015): a suite roda em paralelo
   (`v2/backend/pytest.ini:14` — `django_db_suffix = _{worker_id}`). Portanto:
   sufixar CPFs/usernames com UUID, **nunca** usar `AuditLog.objects.all().delete()`, e
   contar sempre com queryset filtrado — nunca `.count()` global.

## Cobertura

| Lado | Threshold configurado | Enforçado no CI? |
|---|---|---|
| Backend | **85%** — `v2/backend/pytest.ini:40` (`fail_under = 85`) | ✅ sim — `.github/workflows/ci.yaml:353` (`coverage report --fail-under=85`) |
| Frontend | **70%** (statements/branches/functions/lines) — `v2/frontend/vitest.config.ts:44-49` | ❌ **não** — `.github/workflows/frontend-ci.yml:66` roda `npm run test` (= `vitest`), não `test:coverage` |

Política e histórico do gate de 85%: [analysis/COVERAGE_POLICY.md](./analysis/COVERAGE_POLICY.md).
O alvo de 90% (Fase 2) segue como meta, não como gate.

> ⚠️ O threshold de 70% do frontend existe no `vitest.config.ts` mas **nenhum workflow o executa**.
> Quem lê só a config assume que o gate está ativo; não está.

## Baseline CI

**Suite completa**: `1942 passed, 28 skipped, 0 failed`
(ADR-015 §Baseline — [ADR-015-testing-policy.md](../../docs/architecture/project-decisions/ADR-015-testing-policy.md), linha 24;
baseline estabelecido no PR #1030).

*(Corrigido em 2026-07-24: este documento citava `809 passed, 27 skipped` da Issue #69 — baseline de
2025, defasado por um fator de ~2,4. O SSOT do baseline é o ADR-015.)*

## Referências

- **ADR-015** — [Política de Testes](../../docs/architecture/project-decisions/ADR-015-testing-policy.md) (SSOT: baseline, xdist-safety, ordem de validação)
- **COVERAGE_POLICY** — [analysis/COVERAGE_POLICY.md](./analysis/COVERAGE_POLICY.md)
- **CP-01 a CP-06**: Cláusulas Pétreas (REQUIRE_DOCKER, PA, RD, etc.)
- **Contexto Consolidado v2**: regras de negócio no `CLAUDE.md` da raiz do repositório
