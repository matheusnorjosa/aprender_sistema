# Requisitos Funcionais (RF)

Requisitos funcionais do sistema Aprender Sistema v2.

## RF01: Autenticação

- Login via username/password
- Sessão com duração de 2 horas
- CSRF token obrigatório em todas as requisições
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

- Checagem de disponibilidade antes de criar solicitação
- Regras implementadas (RD-01 a RD-08):
  - Não-sobreposição de eventos
  - Bloqueios totais (T) e parciais (P)
  - Buffer de deslocamento entre municípios
  - Capacidade diária por formador
- Exibição visual de conflitos com códigos (E/M/D/P/T/X)

## RF04: Aprovar/Reprovar

- Apenas Superintendência pode aprovar/reprovar (fluxo SUPER)
- Interface dedicada em `/aprovacoes`
- Registro de justificativa em reprovações
- AuditLog de todas as ações
- Aprovação em lote disponível

## RF05: Publicar no Google Calendar

- Publicação de eventos aprovados
- Integração via Service Account
- Suporte a dry-run (simulação)
- Controle de send_updates (notificações)
- Sincronização idempotente

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

| RF | Descrição | Status |
|----|-----------|--------|
| RF01 | Autenticação | ✅ Implementado |
| RF02 | Solicitar Evento | ✅ Implementado |
| RF03 | Verificar Conflitos | ✅ Implementado |
| RF04 | Aprovar/Reprovar | ✅ Implementado |
| RF05 | Google Calendar | ✅ Implementado |
| RF06 | Google Meet | ✅ Implementado |
| RF07 | Resync/Cancel | ✅ Implementado |
| RF08 | Dashboards | ✅ Implementado |
