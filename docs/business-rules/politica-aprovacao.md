# Política de Aprovação (PA)

Regras que governam o fluxo de aprovação de solicitações.

!!! info "SSOT técnica"
    O contrato detalhado — enforcement real por arquivo, idempotência, auditoria e as
    divergências vivas entre a regra e o código — está em
    [`v2/docs/specs/domain/politica-aprovacao.spec.md`](https://github.com/matheusnorjosa/aprender_sistema/blob/main/v2/docs/specs/domain/politica-aprovacao.spec.md).
    Esta página é o resumo legível. Em caso de conflito, a spec vence.

## PA-01: Sem Auto-Aprovação

Uma `Solicitacao` **nunca** muda para "Aprovada" automaticamente, mesmo se não houver conflitos.

!!! warning "Exceção"
    Projetos com `fluxo='NAO_SUPER'` são auto-aprovados na criação.

## PA-02: Perfil Exigido

Podem aprovar/reprovar:

- **superuser**, ou
- **Gerente da Superintendência** (Setor `Superintendência` + Função `Gerente`), ou
- **Assistente Administrativo do Controle** (Setor `Controle` + Função `Assistente Administrativo`)

DAT, Controle puro e Gerente pedagógico **não** aprovam.

```python
# apps/core/rbac/policies.py:395-421 (_user_has_solicitation_approvals)
pode_aprovar = is_superuser OR (
    "Gerente" IN grupos AND "Superintendência" IN grupos
) OR assistente_administrativo_do_controle
```

!!! danger "A autoridade não é imutável hoje (P0 · #1610)"
    O import de usuários permite que um membro do grupo **DAT** conceda a si próprio
    `Gerente` + `Superintendência` — o composite acima — e passe a aprovar.
    `POST /api/usuarios/import/?dry_run=false` devolve HTTP 200 e aplica os grupos
    (`apps/core/services/usuarios_import.py:374-382`, sem allowlist nem checagem ator × alvo).
    Enquanto #1610 estiver aberto, PA-02 descreve o gate, não a fronteira de confiança.

## PA-03: Gatilhos Pós-Aprovação

Integrações externas (Google Calendar, Meet) só executam **após** aprovação manual concluída.

## PA-04: Estado Inicial

Solicitação de projeto com `fluxo='SUPER'` nasce com `status='pendente'`.
Projeto com `fluxo='NAO_SUPER'` nasce `'aprovado'`
(`apps/core/services/solicitacao_create.py:23-44`, `resolve_initial_status`).

!!! danger "Lavagem de aprovação (P1 · #1624)"
    Editar uma solicitação `NAO_SUPER` (nascida `aprovado`) trocando o **projeto** para um de
    fluxo `SUPER` mantém `status='aprovado'`: `perform_update` não reavalia
    `resolve_initial_status` nem reseta o status
    (`apps/core/views_solicitacao.py:401-497`). O evento fica `SUPER` e aprovado sem nunca ter
    tido um `AuditLog` de `APPROVE`.

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

1. Coordenador cria solicitação → checagem de disponibilidade de **todos** os participantes; conflito bloqueia a criação (400 `availability_conflict`) → `status='pendente'`
2. Gerente da Superintendência ou Assistente Administrativo do Controle aprova/reprova.
   Aprovar **revalida** a disponibilidade (#1452): se algum participante entrou em conflito
   desde a criação, a aprovação é recusada com 400
3. Se aprovado → vai para Pré-Agenda
4. Controle publica no Google Calendar

### Aprovação em lote

Máximo 100 IDs por chamada (`POST /api/solicitacoes/batch_approve/`). Cada item gera
`AuditLog` próprio com `batch: true`, e cada item é revalidado contra disponibilidade antes
de ser aprovado.

!!! warning "`ids` não é validado como lista de inteiros (P2 · #1650)"
    Enviar `ids` como **string** passa pelas guardas (`len` conta caracteres) e o Django itera
    a string: `"123"` alveja as solicitações 1, 2 e 3. O ator já precisa da permissão de
    aprovação, então não é escalação — o dano é aprovar alvo que não foi nomeado
    (`apps/core/views_solicitacao.py:857`, `apps/core/services/solicitacao_approval.py:272-291`).

### NAO_SUPER (Auto-aprovado)

1. Coordenador cria solicitação → `status='aprovado'`
2. Vai direto para Pré-Agenda
