# Quick Start

Guia rápido para começar a usar o sistema.

## 1. Acesse o Sistema

Após a [instalação](installation.md), acesse:

- **Frontend**: http://localhost:5173
- **Backend API**: http://localhost:8002/api/

## 2. Crie um Superusuário

```bash
docker compose -f v2/infra/docker-compose.yml exec web python manage.py createsuperuser
```

## 3. Acesse o Admin

Acesse http://localhost:8002/admin/ com as credenciais criadas.

## 4. Fluxo Básico

### Criar Solicitação

1. Acesse `/solicitacoes/nova`
2. Preencha os dados do evento
3. Selecione formadores
4. Sistema verifica conflitos automaticamente
5. Submeta a solicitação

### Aprovar Solicitação (Superintendência)

1. Acesse `/aprovacoes`
2. Revise solicitações pendentes
3. Aprove ou reprove com justificativa

### Publicar no Google Calendar (Controle)

1. Acesse `/pre-agenda`
2. Selecione eventos aprovados
3. Clique em "Publicar"
4. Sistema cria evento no Google Calendar com Meet

## Próximos Passos

- [Arquitetura do Sistema](../architecture/overview.md)
- [Regras de Negócio](../business-rules/clausulas-petreas.md)
- [RBAC e Permissões](../guides/rbac.md)
