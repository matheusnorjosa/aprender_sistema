# Verification — Imports (export-contract / DRF)

ETL legado (`apps.dat_ingest`) foi REMOVIDO. Import atual:
- `import_export_contract` (mgmt command) — **dry-run por padrão**; escreve só com `--apply` **e** `--allow-entity` (sem allowlist, `--apply` é bloqueado e nada é escrito).
- targets `make` / endpoints DRF (ex.: `make import-compras-dry FILE=...`).

## 1. Dry-run sem erros

```bash
# target make (dry-run; nunca grava)
make import-compras-dry FILE=...

# pipeline export-contract (sem --apply = dry-run por padrão; --path é obrigatório)
docker exec aprender_dev-web-1 python manage.py import_export_contract --path /caminho/export-contract
```

## 2. Contagens corretas

O command imprime por entidade `create=`/`update=`/`skip=`. Confira os números:

```bash
docker exec aprender_dev-web-1 python manage.py import_export_contract --path /caminho/export-contract \
  | grep -E "create=|update=|skip="
```

**Evidência necessária:** dry-run termina com exit code 0 e as contagens por entidade batem com o esperado. Lembre: `--apply` sem `--allow-entity` é bloqueado — verifique o aviso `--apply BLOQUEADO` no output antes de afirmar que "nada foi escrito".
