# Go-Live Checklist

> **Histórico, não pendência.** O go-live do AS v2 já ocorreu; produção roda
> `v2026.07.18-94f2765` com 148 usuários ativos. Este checklist é mantido como
> referência de *o que precisa estar verde* antes de uma promoção — não como uma
> lista de tarefas por fazer.
>
> O procedimento operacional canônico é o
> **[Deploy Checklist](https://github.com/matheusnorjosa/aprender_sistema/blob/main/v2/docs/DEPLOY_CHECKLIST.md)**;
> o mecanismo está em
> **[deploy.spec.md](https://github.com/matheusnorjosa/aprender_sistema/blob/main/v2/docs/specs/infra/deploy.spec.md)**.

## Pré-Requisitos

### Infraestrutura

- [ ] Servidor provisionado (4GB RAM, 20GB disco)
- [ ] Docker Engine 24+ instalado
- [ ] Docker Compose v2 instalado
- [ ] Domínio configurado (DNS)
- [ ] Certificado SSL (Let's Encrypt ou similar)
- [ ] Firewall configurado (portas 80, 443)

### Configurações

- [ ] `stack.env` de produção configurado no Portainer (o `.env.production` do repo é template)
- [ ] `SECRET_KEY` gerada (única para produção)
- [ ] `ALLOWED_HOSTS` configurado
- [ ] `DEBUG=False`

### Banco de Dados

- [ ] PostgreSQL 15 configurado
- [ ] Credenciais seguras
- [ ] Backup automatizado **funcionando e verificado por restore drill** — ver
      [Backup](backup.md): hoje o job está morto/silencioso (#1455) e a ferramenta
      oficial de restore rejeita todo artefato `.age` de produção (#1611)
- [ ] Migrations aplicadas — em prod o serviço one-shot `migrate` roda antes de
      `web`/`worker`/`beat` (`docker-compose.prod.yml`)

### Google Calendar

Produção usa **OAuth**, não service account:

- [ ] `GCAL_CLIENT=google`
- [ ] `GCAL_AUTH_MODE=oauth`
- [ ] `GCAL_OAUTH_CLIENT_ID` / `GCAL_OAUTH_CLIENT_SECRET` / `GCAL_OAUTH_REDIRECT_URI`
- [ ] `GCAL_ENCRYPTION_KEY` (Fernet, criptografia dos tokens — SEC-011)
- [ ] `GCAL_ALLOWED_DOMAIN` e `GCAL_CALENDAR_ID`

Detalhe em **[GUIDE_GCAL.md](https://github.com/matheusnorjosa/aprender_sistema/blob/main/v2/docs/GUIDE_GCAL.md)**.

### Monitoramento

- [ ] Sentry configurado (`SENTRY_DSN`) — hoje **ausente** em produção, o que torna
      silenciosa qualquer falha de task Celery
- [ ] Prometheus/Grafana: **não rodam em produção** (só `make up-obs` local);
      o app expõe `/metrics` gated para scraping externo
- [ ] Alertas configurados

## Deploy

Produção **não** sobe por `make up` — esses alvos apontam para `localhost:8002`, ou
seja, o ambiente local. O caminho real é o pull-based (ADR-018):

1. Merge na `main` → `deploy.yaml` builda, escaneia, assina e publica a tag imutável
   `vYYYY.MM.DD-<sha7>`. **Isso não deploya.**
2. `promote.yml` (`workflow_dispatch`, gated no Environment `production` com required
   reviewer) assina o ponteiro no branch `deploy-pointer`.
3. O agente `aprender-deployer` na VM01 verifica assinatura + digests e aplica em
   `127.0.0.1:9443`, confirmando `localhost/api/readyz/` e `/api/version/` de dentro
   da VM antes de selar a `sequence`.

Ver [Deploy](deploy.md).

## Verificações Pós-Deploy

### Funcionais

- [ ] `/api/version/` reporta a tag promovida
- [ ] Login funciona
- [ ] Criar solicitação funciona
- [ ] Aprovar solicitação funciona
- [ ] Publicar no Calendar funciona
- [ ] Meet link é gerado

### Compras (fronteira de domínio)

- [ ] `/controle/compras` mostra dados de `core_compra` (com campo `quantidade`).
- [ ] `/dat/compras-materiais` mostra dados de `core_dat_compra` (materiais/estoque DAT).
- [ ] Criar solicitação aceita apenas município+projeto elegível em `core_compra`.
- [ ] Alterações em `core_dat_compra` não mudam elegibilidade de solicitação.

### Técnicas

- [ ] Logs sem erros críticos
- [ ] Métricas coletando
- [ ] Sentry recebendo eventos (bloqueado enquanto `SENTRY_DSN` estiver ausente)
- [ ] HTTPS funcionando
- [ ] CSRF funcionando

### Performance

- [ ] Tempo de resposta < 500ms
- [ ] Memória estável
- [ ] CPU estável

## Rollback

Rollback é uma **promoção assinada da tag anterior**, não um `git checkout`: rode o
`promote.yml` com o input `rollback: true` apontando para a release anterior (o agente
continua exigindo `sequence` maior que o selo — o anti-rollback protege contra replay,
não contra downgrade deliberado).

`make ban-v1` (`v2/scripts/ban_v1.sh`) não faz parte de rollback: ele remove containers
e redes do projeto Docker legado `aprendersistema` e é higiene de máquina local.

## Comunicação

### Antes do Go-Live

- [ ] Notificar stakeholders
- [ ] Agendar janela de manutenção
- [ ] Preparar comunicado de lançamento

### Após Go-Live

- [ ] Confirmar sucesso com stakeholders
- [ ] Monitorar primeiras horas
- [ ] Coletar feedback inicial

## Contatos

| Função | Responsável | Contato |
|--------|-------------|---------|
| Tech Lead | - | - |
| DevOps | - | - |
| Produto | - | - |

## Histórico

| Data | Versão | Status |
|------|--------|--------|
| 2026-07-18 | `v2026.07.18-94f2765` | em produção |
