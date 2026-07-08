# Egress allowlist da VM01 (agente pull-based)

O agente só precisa alcançar um conjunto pequeno e fixo de destinos. Restringir o
egress reduz a superfície (exfil de token, C2) e é **defesa-em-profundidade** — a
integridade já vem das assinaturas; o egress fechado corta abuso.

## Destinos permitidos (saída)

| Destino | Porta | Para quê |
|---|---|---|
| `raw.githubusercontent.com` | 443 | ler o ponteiro `production.json` + assinatura |
| `registry-1.docker.io`, `auth.docker.io` | 443 | resolver digest (advisory) + pull das imagens pelo daemon |
| `production.cloudflare.docker.com` | 443 | blobs do Docker Hub |
| `fulcio.sigstore.dev`, `rekor.sigstore.dev`, `tuf-repo-cdn.sigstore.dev` | 443 | cosign / attestation (se não usar só trusted-root pinado) |
| host de `NOTIFY_URL` | 443 | notificação write-only |
| `127.0.0.1` | 9443, 8000 | Portainer local + confirmação on-box |

Tudo o mais: **negar**. `api.github.com` **não** é necessário no caminho quente
(`gh attestation verify --bundle-from-oci` lê do próprio registry).

## Exemplo nftables (revisar antes de aplicar — precisa de root)

```nft
# saída do usuário do agente (uid do aprender-deployer/applier) só para :443/:9443/:8000
# resolver os IPs/hosts via um proxy allowlist (ex.: tinyproxy/squid) é mais robusto
# que allowlist por IP (CDNs mudam de IP). Preferir egress via proxy com ACL de host.
```

> Recomendação: egress via **proxy HTTP(S) com ACL de host** (os CDNs do Docker Hub
> e do Sigstore trocam de IP). Allowlist por IP é frágil. Documentar o proxy aqui
> quando definido (Fase 4).
