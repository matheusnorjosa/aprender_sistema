# Política de Aprovação (PA)

Regras que governam o fluxo de aprovação de solicitações.

## PA-01: Sem Auto-Aprovação

Uma `Solicitacao` **nunca** muda para "Aprovada" automaticamente, mesmo se não houver conflitos.

!!! warning "Exceção"
    Projetos com `fluxo='NAO_SUPER'` são auto-aprovados na criação.

## PA-02: Perfil Exigido

Apenas usuários com **Gerente + Superintendência** (ou superuser) podem aprovar/reprovar.

```python
can_approve_super = is_superuser OR (
    "Gerente" IN funcoes AND "Superintendência" IN setores
)
```

## PA-03: Gatilhos Pós-Aprovação

Integrações externas (Google Calendar, Meet) só executam **após** aprovação manual concluída.

## PA-04: Estado Inicial

Toda solicitação nasce com `status = 'pendente'`.

## PA-05: Auditoria

Registrar em `AuditLog`:

- Usuário que aprovou/reprovou
- Data/hora da ação
- Justificativa (quando houver)

## PA-06: UI/UX

- Botões de ação ocultos para perfis sem permissão
- Conformidade ISO 9241-110 (controle explícito)

## PA-07: Testes Obrigatórios

```python
test_never_auto_approves_on_clean_or_save
test_only_superintendencia_can_approve_or_reject
test_calendar_integration_not_called_before_approval
test_approval_flow_records_audit_log
test_non_privileged_user_gets_403_on_approval_endpoint
```

## Fluxos

### SUPER (Manual)

1. Coordenador cria solicitação → `status='pendente'`
2. Superintendência aprova/reprova
3. Se aprovado → vai para Pré-Agenda
4. Controle publica no Google Calendar

### NAO_SUPER (Auto-aprovado)

1. Coordenador cria solicitação → `status='aprovado'`
2. Vai direto para Pré-Agenda
