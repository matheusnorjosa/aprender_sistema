# Security Policy

## Reportar Vulnerabilidades

- **Email**: <security@aprender.gov.br>
- **GitHub**: [Security Advisories](https://github.com/matheusnorjosa/aprender_sistema/security/advisories)

**Nao crie issues publicas para vulnerabilidades.**

---

## Medidas Implementadas

| Medida | Descricao |
| ------ | --------- |
| Rate Limiting | 5 tentativas/minuto no login (429 se exceder) |
| Upload Validation | Max 10MB, apenas CSV/XLS/XLSX |
| Audit Logs | Login/logout registrados com IP e user-agent |
| CSRF HttpOnly | Token protegido contra XSS |
| Usuarios Inativos | Bloqueio automatico no login |

---

## Checklist de Deploy

- `DEBUG = False`
- `SECRET_KEY` em variavel de ambiente
- `SECURE_SSL_REDIRECT = True`
- `SESSION_COOKIE_SECURE = True`
- `CSRF_COOKIE_SECURE = True`
- PostgreSQL com privilegios minimos
- Redis com senha configurada

---

## Supply Chain (SLSA + Cosign)

- Workflow operacional: `.github/workflows/slsa-provenance.yml`
- Gera attestations SLSA v1 para imagens Docker publicadas.
- Assina imagens com Cosign keyless (OIDC GitHub Actions).
- Verifica assinatura e provenance na mesma execucao.

### Verificacao manual (exemplo)

```bash
# assinatura
cosign verify norjosamatheus/aprender-backend@sha256:<digest> \
  --certificate-oidc-issuer https://token.actions.githubusercontent.com \
  --certificate-identity-regexp "^https://github.com/matheusnorjosa/aprender_sistema/.github/workflows/slsa-provenance.yml@refs/(heads/main|tags/.+)$"

# attestation/provenance
gh attestation verify oci://norjosamatheus/aprender-backend@sha256:<digest> \
  --repo matheusnorjosa/aprender_sistema \
  --signer-workflow matheusnorjosa/aprender_sistema/.github/workflows/slsa-provenance.yml \
  --bundle-from-oci
```

---

## Contato

- **Security Team**: <security@aprender.gov.br>
- **Project Lead**: @matheusnorjosa

---

Atualizado: 2026-03-20
