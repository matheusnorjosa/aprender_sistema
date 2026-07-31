# Guia de Integração Google Calendar

> Conteúdo consolidado nos SSOTs do tema (fora do MkDocs deste site):
>
> - **Spec canônica (contrato + invariantes)**: [`specs/backend/gcal.spec.md`](https://github.com/matheusnorjosa/aprender_sistema/blob/main/v2/docs/specs/backend/gcal.spec.md)
> - **Guia operacional completo**: [`GUIDE_GCAL.md`](https://github.com/matheusnorjosa/aprender_sistema/blob/main/v2/docs/GUIDE_GCAL.md)

O guia completo cobre autenticação (Service Account e OAuth), variáveis de ambiente, matriz `apply_blocked`/`dry_run`, modalidade online/presencial (Meet), resync/cancel e criptografia de tokens (SEC-011).

## Qual modo roda onde

| Ambiente | `GCAL_CLIENT` | `GCAL_AUTH_MODE` |
|---|---|---|
| dev (default) | `fake` — cliente in-memory, nada chega ao Google | n/a |
| produção | `google` | `oauth` (cliente real; **não** service account) |

Em produção `GCAL_SERVICE_ACCOUNT_JSON` não existe: a autenticação é OAuth, com
`GCAL_OAUTH_CLIENT_ID`/`_SECRET`/`_REDIRECT_URI`, `GCAL_ENCRYPTION_KEY` (Fernet) e
`GCAL_ALLOWED_DOMAIN=aprendereditora.com.br`.
