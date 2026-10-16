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

Podem aprovar/reprovar, nesta ordem (`solicitation_approval_basis`, rótulo gravado no AuditLog):

1. **superuser** (`superuser`);
2. **Gerente da Superintendência** por vínculo vigente na gerência `SUPERINTENDENCIA`
   (`gerente_superintendencia`), só no fluxo SUPER dessa gerência;
3. **Assistente Administrativo do Controle** (`asst_admin_controle`), até o PR 11;
4. o par legado de grupos `Superintendência` + `Gerente` (`grupo_superintendencia_gerente`), até o B2;
5. **o DAT** (`capacidade_aprovar`, PR 10; decisão do dono de 02/10, nº 16): quem tem a capacidade
   `approve_solicitation`, que vem só do pacote `ADMIN_OPERACIONAL` (vínculo EQUIPE ou GERENTE
   vigente na gerência DAT). Decide solicitação de qualquer gerência e fluxo.

Controle puro, Gerente pedagógico, Diretoria e o grupo DAT sem o vínculo **não** aprovam.

**Segregação** (o superuser pode, como break-glass marcado no AuditLog):

- ninguém decide a **própria** solicitação (`self_approval_forbidden`);
- quem **alterou a conta** do autor pela tela de Usuários (criar, editar qualquer campo, senha,
  ativar ou desativar, grupos, anonimizar) não decide as solicitações dele por **30 dias**,
  contados da decisão ou da criação da solicitação, o que vier antes
  (`altered_account_approval_forbidden`); vale ao contrário: quem teve a **senha redefinida** pelo
  autor também não decide as solicitações dele no mesmo prazo
  (`approver_account_altered_by_author_forbidden`); nem quem teve a senha redefinida pela mesma
  pessoa que alterou a conta do autor (`accounts_altered_by_same_person_forbidden`). Do lado de quem
  decide só a senha conta (corrigir o nome dela não dá a conta a ninguém). Alteração feita pelo
  superuser não conta nesses dois casos;
- quem **editou** data, horário, município, projeto ou formadores de uma solicitação depois da
  última aprovação dela não a decide (`edited_by_approver_forbidden`). Outra pessoa aprovadora decide.

**Contas** (S4, decisão do dono de 16/10): só o superusuário altera conta de superusuário. Quem tem
`manage_admin_registries` (o DAT) altera as demais, com AuditLog; a senha redefinida por outra
pessoa obriga a troca no próximo acesso.

!!! success "A autoridade não é concedível pelo import (#1610, resolvido)"
    O import de usuários só concede grupo pelo superusuário, e os importadores de equipe recusam
    o vínculo que dá a aprovação. Detalhe na spec.

## PA-03: Gatilhos Pós-Aprovação

Integrações externas (Google Calendar, Meet) só executam **após** aprovação manual concluída.

## PA-04: Estado Inicial

Solicitação de projeto com `fluxo='SUPER'` nasce com `status='pendente'`.
Projeto com `fluxo='NAO_SUPER'` nasce `'aprovado'`
(`apps/core/services/solicitacao_create.py:23-44`, `resolve_initial_status`).

!!! success "Editar a SUPER aprovada pede nova aprovação (#1624, resolvido; estendido em 2026-10-15)"
    Trocar o **projeto** para um de fluxo `SUPER` (#1624), ou mudar **data, horário, município ou
    formadores** de uma SUPER aprovada (decisão do dono, 14/10/2026), devolve a solicitação para
    `pendente`. Observação, local e evento online não devolvem. Detalhe no adendo da PA-04 da spec.

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
test_non_privileged_user_gets_403_on_approval_endpoint
test_segregacao_conta_alterada_bloqueia_decisao
test_calendar_integration_not_called_before_approval
test_calendar_integration_is_called_after_approval
test_approval_flow_records_audit_log
```

## Fluxos

### SUPER (Manual)

1. Coordenador cria solicitação → checagem de disponibilidade de **todos** os participantes; conflito bloqueia a criação (400 `availability_conflict`) → `status='pendente'`
2. Gerente da Superintendência, DAT ou Assistente Administrativo do Controle aprova/reprova
   (nunca a própria, a de autor cuja conta alterou nos 30 dias, nem a que editou).
   Aprovar **revalida** a disponibilidade (#1452): se algum participante entrou em conflito
   desde a criação, a aprovação é recusada com 400
3. Se aprovado → vai para Pré-Agenda
4. Controle, Superintendência ou DAT publica no Google Calendar

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
