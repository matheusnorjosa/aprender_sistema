# Go-Live Checklist

Checklist para entrada em produção do Aprender Sistema v2.

## Pré-Requisitos

### Infraestrutura

- [ ] Servidor provisionado (4GB RAM, 20GB disco)
- [ ] Docker Engine 24+ instalado
- [ ] Docker Compose v2 instalado
- [ ] Domínio configurado (DNS)
- [ ] Certificado SSL (Let's Encrypt ou similar)
- [ ] Firewall configurado (portas 80, 443)

### Configurações

- [ ] `.env` de produção configurado
- [ ] `SECRET_KEY` gerada (única para produção)
- [ ] `ALLOWED_HOSTS` configurado
- [ ] `DEBUG=False`

### Banco de Dados

- [ ] PostgreSQL 15 configurado
- [ ] Credenciais seguras
- [ ] Backup automatizado
- [ ] Migrations aplicadas

### Google Calendar

- [ ] Service Account criada
- [ ] Calendário compartilhado com SA
- [ ] `GCAL_CLIENT=google`
- [ ] Credenciais montadas no container

### Monitoramento

- [ ] Sentry configurado
- [ ] Prometheus/Grafana (opcional)
- [ ] Alertas configurados

## Deploy

```bash
# 1. Subir ambiente
make up

# 2. Verificar readiness
make readyz

# 3. Verificar health
make healthz

# 4. Bloquear v1
make ban-v1
```

## Verificações Pós-Deploy

### Funcionais

- [ ] Login funciona
- [ ] Criar solicitação funciona
- [ ] Aprovar solicitação funciona
- [ ] Publicar no Calendar funciona
- [ ] Meet link é gerado

### Técnicas

- [ ] Logs sem erros críticos
- [ ] Métricas coletando
- [ ] Sentry recebendo eventos
- [ ] HTTPS funcionando
- [ ] CSRF funcionando

### Performance

- [ ] Tempo de resposta < 500ms
- [ ] Memória estável
- [ ] CPU estável

## Rollback

Se necessário reverter:

```bash
# 1. Parar v2
docker compose down

# 2. Restaurar v1 (se aplicável)
git checkout v1-freeze
```

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
| - | v2.0.0 | Planejado |
