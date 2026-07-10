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

## Re-gravar o `bin.sha256` quando um binário do host é atualizado

O `install.sh` valida os 4 binários contra este arquivo **antes** de instalar e
**recusa** se algum hash divergir. Isso é TOFU (*trust on first use*): um
`unattended-upgrade` do `curl` ou do `jq` faz o próximo reinstall parar. É o
mecanismo funcionando — mas exige uma decisão humana, não um `--record-bins` reflexo.

`--record-bins` **pula a validação** e sobrescreve o arquivo com o que estiver no
disco. Usá-lo sem provar a procedência lavaria um binário adulterado para dentro
da raiz de confiança — logo o `curl`, que busca o ponteiro e fala com o Portainer.

**Antes de re-gravar, prove que o binário é o do pacote assinado da distro:**

```bash
PKG=curl                                   # ou jq
VER="$(dpkg-query -W -f='${Version}' "$PKG")"

dpkg -V "$PKG" && echo "dpkg: sem adulteracao"     # md5sums do pacote instalado
grep -i " ${PKG}:" /var/log/dpkg.log | tail -3     # quando mudou, e por quem

# prova forte: baixa o .deb assinado do repo e compara o binario de dentro
cd "$(mktemp -d)" && apt-get download "${PKG}=${VER}"
dpkg-deb --fsys-tarfile ./*.deb | tar -xO "./usr/bin/${PKG}" | sha256sum
sha256sum "/usr/bin/${PKG}"                         # tem de bater byte a byte
```

Se os dois `sha256` forem iguais e o `dpkg -V` estiver limpo, o binário veio de um
pacote assinado pela distro (o `apt` verifica a assinatura do `Release`). Só então:

```bash
cp trust/bin.sha256 /root/adr018-cutover/bin.sha256.antes-$(date -u +%Y%m%dT%H%M%SZ)
bash bootstrap/install.sh --src <arvore> --record-bins
```

Se os hashes **não** baterem, pare: `/usr/bin/curl` divergindo do pacote assinado,
na máquina que verifica assinaturas de deploy, é incidente — não inconveniente.

> Ocorrido real: 2026-07-10, `unattended-upgrade` subiu `curl` de `8.5.0-2ubuntu10.10`
> para `10.11` às 06:28 UTC; o `install.sh` barrou o update do agente 7h depois.
> A prova acima confirmou a procedência e o `--record-bins` foi feito conscientemente.
