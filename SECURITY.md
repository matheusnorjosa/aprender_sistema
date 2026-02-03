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

## Contato

- **Security Team**: <security@aprender.gov.br>
- **Project Lead**: @matheusnorjosa

---

Atualizado: 2026-02-03
