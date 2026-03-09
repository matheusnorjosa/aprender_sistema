# Politica de Documentacao (Repositorio Publico)

Este repositorio e publico. Portanto:

- `v2/docs/` guarda **somente documentacao publica e sanitizada**.
- Conteudo sensivel (IP interno, detalhes de credencial, procedimentos internos, runbooks privados) deve ficar em:
  - `v2/docs/private/` (ignorado pelo Git), ou
  - sistema externo privado (vault/wiki privada).

## Regras rapidas

1. Nunca commitar segredo, token, senha, chave privada ou dump de configuracao real.
2. Em exemplos, usar placeholders (`<token>`, `<senha>`, `<ip-privado>`).
3. Relatorios locais/temporarios devem usar sufixo `.local.md` ou pasta `private/`.
4. Scan reports locais (audit/bandit/pip-audit/npm-audit) nao devem ser versionados.
5. Arquivos `.env` operacionais (`.env.dev`, `.env.staging`, `.env.production`) nao devem ser versionados.
6. Apenas templates `.example` podem ficar publicos (`.env.example`, `.env.*.example`).

## Fluxo recomendado

1. Escreva primeiro em `v2/docs/private/`.
2. Gere versao sanitizada.
3. Publique a versao sanitizada em `v2/docs/`.
