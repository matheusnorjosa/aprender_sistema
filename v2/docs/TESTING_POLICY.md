# Testing Policy — Aprender v2

Este documento consolida práticas e contratos adotados nos testes para manter o CI previsível e fiel ao domínio.

## Ambiente de CI

- **Runtime**: Python 3.11, PostgreSQL 15, Redis 7, TZ `America/Fortaleza`
- **Settings**: `DJANGO_SETTINGS_MODULE=config.settings`, `ENVIRONMENT=testing`, `REQUIRE_DOCKER=0`
- **Integrações externas**:
  - `GCAL_CLIENT=fake`, `GCAL_SEND_UPDATES=none`
- **Diretórios de ETL**:
  - `ETL_OUTPUT_DIR` e `ETL_DATA_DIR` resolvidos no workspace do CI
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

## Seed / ETL / Arquivos

**Paths robustos**:
```python
from pathlib import Path
from django.conf import settings

csv_path = Path(settings.BASE_DIR) / "apps/core/data/projetos_fluxo.csv"
```

**Evitar**:
- Caminhos relativos ao CWD (quebram conforme diretório de execução)
- Hardcoded `/app` (específico de container, não funciona localmente)

**Artefatos de ETL**:
- Devem ser gravados sob `ETL_OUTPUT_DIR` ou `BASE_DIR`, nunca em `/app`

## Princípios

1. **Não remover nem pular testes** por conveniência
2. **Ajustar testes** quando divergirem do "Contexto Consolidado v2"
3. **Ajustar código** só quando o comportamento real estiver incorreto
4. **Fixtures idempotentes**: usar `get_or_create()` para evitar cross-poluição
5. **Security-first**: validar permissões antes de parâmetros (403 → 400 → 200)

## Baseline CI

**Suite completa** (após correções da Issue #69):
```
=========== 809 passed, 27 skipped, 6 warnings in 277.23s (0:04:37) ============
```

**PRs relacionados**:
- #72 - CI/CD alignment (runtime, TZ, fake GCAL)
- #73 - Celery/GCal Safety (FEATURE_AUTO_APPLY)
- #74 - Availability RBAC (security-first 403/400)

## Referências

- **Issue #69**: Correção de testes CI (809/809 passando)
- **CP-01 a CP-06**: Cláusulas Pétreas (REQUIRE_DOCKER, PA, RD, etc.)
- **Contexto Consolidado v2**: Regras de negócio documentadas em `.claude/CLAUDE.md`
