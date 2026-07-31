# Quick Start

Guia rápido para começar a usar o sistema.

## 1. Acesse o Sistema

Após a [instalação](installation.md), acesse:

- **Frontend**: http://localhost:5173
- **Backend API**: http://localhost:8002/api/

## 2. Crie um Superusuário

Todos os comandos abaixo rodam a partir de `v2/infra` (precisam do `--env-file`,
por isso o `make`/`DEV_COMPOSE`; um `docker compose -f docker-compose.yml` puro falha):

```bash
cd v2/infra
docker compose --env-file .env.dev \
  -f docker-compose.yml -f docker-compose.override.yml \
  exec web python manage.py createsuperuser
```

O `Usuario` é customizado: além de `username`/senha, o comando pede um `cpf`
obrigatório e único, de exatamente 11 dígitos (`apps/core/models/usuario.py:22-31`).
O login é `POST /api/auth/login/` com `username` + `password`.

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

> Em dev o default é `GCAL_CLIENT=fake` (cliente in-memory): a publicação é simulada
> e nada chega ao Google.

## Próximos Passos

- [Arquitetura do Sistema](../architecture/overview.md)
- [Regras de Negócio](../business-rules/clausulas-petreas.md)
- [RBAC e Permissões](../guides/rbac.md)
