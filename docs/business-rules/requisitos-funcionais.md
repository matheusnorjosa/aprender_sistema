# Requisitos Funcionais (RF)

Requisitos funcionais do sistema Aprender Sistema v2.

!!! danger "Colisão de numeração — decisão pendente"
    Existe uma **segunda** lista RF01..RF08, com recorte diferente, em
    [`v2/docs/specs/domain/requisitos-funcionais.spec.md`](https://github.com/matheusnorjosa/aprender_sistema/blob/main/v2/docs/specs/domain/requisitos-funcionais.spec.md)
    (lá RF01=Importação, RF02=Solicitação, RF03=Conflitos, RF04=Aprovação, RF05=Google Calendar,
    RF06=Google Meet, RF07=Auditoria, RF08=Mapa mensal). Os dois recortes descrevem
    funcionalidades que existem, mas **`RF01`..`RF08` não são intercambiáveis entre os
    documentos**. Ao citar um RF, diga sempre de qual lista. A unificação ainda não foi decidida.

## RF01: Autenticação

- Login por **CPF ou username** + senha (`apps/core/auth_backends.py:21` —
  `CPFOrUsernameBackend`: entrada com 11 dígitos após remover pontuação é tratada como CPF,
  o resto como username). Na prática o identificador operacional é o CPF
- Sessão com duração default de 2 horas (`SESSION_COOKIE_AGE`, `config/settings.py:333`,
  sobrescrevível por env)
- CSRF token obrigatório nas requisições que alteram estado
- Logout com invalidação de sessão

## RF02: Solicitar Evento

- Coordenador preenche formulário com:
  - Projeto
  - Município
  - Data/hora início e fim
  - Formadores participantes
  - Modalidade (presencial/online)
  - Descrição
- Validação de campos obrigatórios
- Criação com status `pendente` (SUPER) ou `aprovado` (NAO_SUPER)

## RF03: Verificar Conflitos

- Checagem de disponibilidade na criação, na edição e na aprovação — e ela **bloqueia**
  (HTTP 400 `availability_conflict`), não apenas informa
- Checa **todos** os participantes ocupantes do evento, não só quem criou (#1452)
- Regras implementadas (RD-01 a RD-08):
    - Não-sobreposição de eventos
    - Bloqueios totais (T) e parciais (P)
    - Buffer de deslocamento entre municípios
- Não há limite de horas por dia na agenda: desde 05/10/2026 o RD-05 é o teto por evento da
  contagem de horas de formação, não conflito
- Exibição visual de conflitos com códigos D/P/T/X
  (`E` é código de célula da Grade Mensal, não de conflito)

Ver [Regras de Disponibilidade (RD)](regras-disponibilidade.md).

## RF04: Aprovar/Reprovar

- Aprovam/reprovam (fluxo SUPER): superuser, **Gerente da Superintendência**, **DAT** ou
  **Controle** — ver [PA-02](politica-aprovacao.md#pa-02-perfil-exigido)
- Interface dedicada em `/aprovacoes`
- Registro de justificativa em reprovações
- AuditLog de todas as ações
- Aprovação em lote disponível (máx. 100 IDs)
- Aprovar revalida a disponibilidade antes de mudar o status (#1452)

Ver [Política de Aprovação (PA)](politica-aprovacao.md). As três divergências que ela
registrava (#1610, #1624, #1650) estão resolvidas.

## RF05: Publicar no Google Calendar

- Publicação de eventos aprovados
- Dois modos de autenticação, selecionados por `GCAL_AUTH_MODE`: `service_account` (default do
  código) e `oauth` (`apps/core/services/gcal_client_factory.py:83-87`).
  **Produção roda em modo `oauth`** com cliente Google real; não há
  `GCAL_SERVICE_ACCOUNT_JSON` configurado
- Cliente selecionado por `GCAL_CLIENT=fake|google` (`config/settings.py:722`)
- Suporte a dry-run (simulação)
- Controle de send_updates (notificações)
- Sincronização idempotente (`external_event_id = asv2-{id}` + hash do payload)

## RF06: Gerar Link Google Meet

- Geração automática para eventos online (`is_online=true`)
- Link persistido no campo `meet_link`
- Componente `MeetLink` para exibição e cópia

## RF07: Resync/Cancel

- Reenviar evento para sincronizar alterações
- Cancelar evento (remove do Calendar)
- Idempotência garantida (404 = sucesso)

## RF08: Dashboards

- Métricas de eventos por período
- Filtros por projeto, município, status
- Exportação de relatórios

## Status de Implementação

"Implementado" significa que o caminho existe e está em produção — não que esteja livre de
defeito conhecido. As ressalvas abaixo registram o estado de cada RF; as divergências de RF03 e
RF04, reconfirmadas por execução contra `main d08acfa5`, já foram corrigidas no código.

| RF | Descrição | Status | Ressalva |
|----|-----------|--------|----------|
| RF01 | Autenticação | ✅ Implementado | — |
| RF02 | Solicitar Evento | ✅ Implementado | — |
| RF03 | Verificar Conflitos | ✅ Implementado | As duas divergências do #1664 saíram do código: o RD-05 deixou de ser checagem de agenda (05/10/2026) e a query de eventos existentes usa o mesmo predicado de papéis ocupantes (`ocupa_agenda_q`). O épico #1664 segue aberto no GitHub |
| RF04 | Aprovar/Reprovar | ✅ Implementado | Sem divergência viva: o import não concede autoridade (#1610), editar a SUPER aprovada pede nova aprovação (#1624) e o lote valida `ids` (#1650) |
| RF05 | Google Calendar | ✅ Implementado | Produção usa OAuth, não Service Account |
| RF06 | Google Meet | ✅ Implementado | — |
| RF07 | Resync/Cancel | ✅ Implementado | — |
| RF08 | Dashboards | ✅ Implementado | — |
