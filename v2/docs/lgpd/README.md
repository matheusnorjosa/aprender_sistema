# Governança LGPD — Aprender Sistema v2

Reúne a parte **organizacional** da conformidade LGPD. Veredito da auditoria de risco
(2026-08): **engenharia de segurança forte, conformidade formal a completar** — o risco real
é reclamação de titular à ANPD sobre transparência/governança, não vazamento.

## O que este scaffold entrega (estrutura + placeholders)

| Item | Onde | Estado |
|------|------|--------|
| Política de Privacidade | `components/lgpd/PoliticaPrivacidadeContent.tsx` + rota `/politica-privacidade` + link na PerfilPage | conteúdo técnico real; jurídico completa os `[A PREENCHER]` |
| Aviso de transparência no login (art. 9º) | `components/lgpd/AvisoTransparenciaLGPD.tsx` (na LoginPage) | pronto; falta base legal + contato do DPO |
| Runbook de incidente (art. 48) | `RUNBOOK_INCIDENTE_ANPD.md` | template; falta contatos/prazos internos |

## O que depende do controlador + advogado (preencher os `[A PREENCHER]`)

1. **Identificação do controlador**: razão social, CNPJ, endereço.
2. **Encarregado (DPO)**: nome + e-mail/canal de contato (usado na Política, no aviso e no runbook).
3. **Base legal** por categoria de dado (arts. 7º/11). Para sistema interno de colaboradores,
   tipicamente **não é consentimento** — execução de contrato / obrigação legal / legítimo interesse.
4. **Prazos de retenção** oficiais por categoria.
5. **Versão e data de vigência** da Política.
6. **Canal/procedimento vigente da ANPD** para comunicação de incidente.

## Base TÉCNICA já implementada (dá suporte à governança)

- **Direitos do titular (art. 18)** self-service em *Meu perfil*: acesso, correção de contato,
  exportação (portabilidade). Exclusão via **anonimização** (`apps/core/services/anonimizacao.py`).
- **Retenção/expurgo** automático: AuditLog e artefatos de importação (tasks Celery beat).
- **Trilha de auditoria** transacional (ator + fato, sem PII); export do titular auditado.
- **Segurança do tratamento (art. 46)**: TLS/HSTS, backups cifrados (`age`), RBAC + row-level,
  segredos fail-closed, redação de PII no log, minimização de PII na transferência ao Google.
- **Atribuição de licenças**: `frontend/public/THIRD-PARTY-NOTICES.txt`.

## Achado operacional pendente (fora deste scaffold)

- Em produção, `GCAL_SEND_UPDATES` deve ser `all`/`externalOnly` (formadores precisam ser
  notificados por e-mail), não o default `none`.

## Referências

- Auditoria + sweep técnico: memória `project_lgpd_audit_and_sweep_2026_08`.
- Specs de segurança: `v2/docs/specs/backend/` (rbac, backup-dr) e `specs/infra/at-rest-encryption.spec.md`.
