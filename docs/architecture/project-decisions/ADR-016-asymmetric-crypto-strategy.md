# ADR-016: Estratégia de Criptografia Assimétrica

**Status:** Accepted
**Date:** 2026-04-13
**Decider:** Matheus Norjosa

## Context

O sistema usa criptografia simétrica (Fernet/AES-128) para tokens OAuth em repouso. Não há uso de criptografia assimétrica (RSA/ECC/EdDSA) na aplicação. É necessário definir formalmente se e quando adotar.

## Decision

**Não adotar criptografia assimétrica no momento.** A criptografia simétrica via Fernet atende todos os requisitos atuais de proteção de tokens OAuth.

### Justificativa

- Tokens OAuth são segredos internos (server-to-server), não precisam de não-repúdio
- Não há troca de chaves entre partes distintas (cenário clássico de assimétrica)
- Fernet (AES-128-CBC + HMAC-SHA256) é suficiente para encryption-at-rest
- Complexidade de gestão de chaves assimétricas (PKI, revogação, rotação) não se justifica

### Gatilhos de Adoção

Criptografia assimétrica será **obrigatória** quando qualquer cenário abaixo surgir:

1. **Assinatura de payloads B2B** — webhooks enviados a terceiros que precisam verificar autenticidade
2. **Validação de webhooks recebidos** — verificar assinatura de providers externos
3. **Tokens com chave pública** — emitir JWTs assinados consumidos por serviços externos
4. **Não-repúdio** — auditoria legal que exija prova criptográfica de autoria

### Padrão Técnico Futuro (quando adotado)

| Aspecto | Padrão |
| ------- | ------ |
| Algoritmo de assinatura | Ed25519 (preferido) ou ECDSA P-256 |
| Algoritmo de criptografia | RSA-OAEP com SHA-256 (interop) ou X25519 |
| Biblioteca | `cryptography` (já usada para Fernet) |
| Gestão de chaves | Variável de ambiente + rotação via management command |
| Formato de chave | PEM (privada) / JWK (pública, se API) |

## Consequences

**Positivo:**

- Zero complexidade adicional de PKI
- Decisão documentada evita ambiguidade futura
- Gatilhos objetivos permitem adoção deliberada quando necessário

**Negativo:**

- Risco residual: se um cenário de gatilho surgir sem ser identificado, pode haver delay na adoção

**Risco Residual:** Aceito. Revisão programada no próximo ciclo de segurança.

## References

- SEC-012: Issue #865
- SEC-011: Governança de criptografia OAuth (#864)
- OWASP Cryptographic Failures
