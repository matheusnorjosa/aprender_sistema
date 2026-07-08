# `trust/` — âncoras de confiança do agente

Estes arquivos são a **raiz de confiança** da verificação. São tratados como
**código** (versionados, e no host ficam `read-only` + `chattr +i` sob
`/opt/aprender-deployer/current/trust/`), **nunca** em `/etc`. Se um atacante
puder editá-los, ele redireciona a verificação — por isso são imutáveis.

| Arquivo | O que é | Origem |
|---|---|---|
| `identity.env` | Emissor OIDC, regexes de identidade (ponteiro/imagem), repos allowlisted, signer-workflow | Versionado (este PR) |
| `compose.pinned.yml` | SSOT do `StackFileContent` reenviado no PUT; alvo do `compose_check_drift` | **Gerado no bootstrap** (forma normalizada do Portainer) |
| `sigstore-root.json` | Trusted-root do Sigstore **pinado offline** (`cosign --trusted-root`) | **Gerado no bootstrap** (ver abaixo) |
| `bin.sha256` | Hashes de `cosign`/`gh`/`jq`/`curl` esperados no host | **Preenchido no install** para os binários do host |

## Gerar o `sigstore-root.json` (pin offline)

O pin offline resiste a spoof de Rekor/TUF e evita DoS por mudança de CDN:

```bash
cosign trusted-root create > trust/sigstore-root.json
# revisar, então pinar imutável no host (install.sh aplica chattr +i)
```

Sem este arquivo, `cosign verify` (que usa `--trusted-root`) **falha-fechado**
(REFUSE) — comportamento correto: o agente nunca deploya sem raiz de confiança.

## Gerar o `compose.pinned.yml`

Capturado no bootstrap a partir do `GET /api/stacks/{id}/file` **depois** do PUT
inicial na forma Opção-B (imagens por `@${DIGEST:?}`), garantindo byte-estabilidade
com a normalização do Portainer. Ver `bootstrap/migrate-stack.sh`.
