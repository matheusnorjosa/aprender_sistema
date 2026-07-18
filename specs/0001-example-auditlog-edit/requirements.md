# Requirements — reabilitar AuditLog de edição de Solicitação

> Exemplo real (concluído). Mostra granularidade e tom esperados.

- **Spec ID**: 0001-example-auditlog-edit
- **Issue(s)**: #1382
- **Branch**: `test/1382-auditlog-edicao-solicitacao`
- **Autor**: Matheus
- **Status**: pronto p/ PR (verde local; aguarda staging gate + decisão do humano)

## Problema

`test_edit_creates_audit_log` em `apps/core/tests/test_solicitacao_edit.py` estava
`@pytest.mark.skip` com TODO de "investigação". Edição comum de `Solicitacao` ficava sem
cobertura de AuditLog, enquanto approve/reject/delete tinham — lacuna concreta em PA-05.

## Objetivo

Garantir, por teste, que editar uma Solicitação registra `AuditLog` com os campos alterados.

## User stories

- Como auditor, quero que toda edição de Solicitação fique no AuditLog, para rastrear quem
  mudou o quê.

## Critérios de aceite (testáveis)

- [x] O teste não está mais skipado.
- [x] PATCH com mudança real cria `AuditLog` `action=UPDATE`.
- [x] PATCH sem mudança não cria log falso.
- [x] O log contém usuário, `solicitacao_id` e `changed_fields` (old/new).
- [x] Testes existentes continuam verdes.

## Regras de negócio aplicáveis

- **PA-05** — registrar usuário, data/hora e o que mudou em `AuditLog`.
- **CP-02** — toda ação de aprovação/edição relevante é auditada.

## Fora de escopo

- Refatorar o sistema de auditoria; mexer na tela de Audit Logs; criar novo modelo.

## Riscos / questões em aberto

- Suspeita inicial: divergência entre serializer/`perform_update`/fixtures. (Não se
  confirmou — ver `design.md`.)
