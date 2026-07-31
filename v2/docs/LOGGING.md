# Guia de Logging - AS v2

**Data**: 2026-07-24 (revisão contra o código)
**Status**: Ativo
**Issue**: #227

> **Onde os logs vivem em produção:** no **stdout dos containers**, coletado pelo driver
> `json-file` do Docker com rotação `max-size: 50m` / `max-file: 10`
> (`v2/infra/docker-compose.prod.yml`). **Não há Loki, nem ELK, nem agregador** — ver
> [OBSERVABILITY.md](./OBSERVABILITY.md). Para investigar um incidente:
> `docker compose logs --tail=N <serviço>`, lembrando que `web`, `worker` e `beat` têm
> logs **separados** (o campo `service` no JSON identifica a origem). Com a rotação acima,
> o histórico é finito: **em incidente, colete os logs antes de reiniciar qualquer coisa.**

---

## Objetivo

Este guia documenta as práticas de logging do projeto para garantir:
- Logs estruturados em produção
- Sem exposição de dados sensíveis
- Consistência entre backend e frontend
- Debugging efetivo em desenvolvimento

---

## Backend (Python/Django)

### Logger Estruturado

O backend usa `logging.getLogger(__name__)` com configuração estruturada (MP2).

```python
import logging

logger = logging.getLogger(__name__)

# Níveis de log
logger.debug("Detalhes técnicos (só em dev)")
logger.info("Operações normais")
logger.warning("Avisos importantes")
logger.error("Erros que precisam atenção")
```

### Configuração

A configuração está em `config/settings.py:632-690` (bloco `LOGGING`):

- **Development**: formatter `verbose`, legível no console
- **Staging/Production**: formatter `json` (`pythonjsonlogger`) em stdout, com os filtros
  `RequestIDFilter` e `ContextFilter` (`apps/core/logging_filters.py`) injetando
  `request_id`, `environment` e `service`
- `SERVICE_NAME` (`web`/`worker`/`beat`) vem do compose e é o que permite distinguir a
  origem da linha

### Boas Práticas

```python
# ✅ CORRETO: Usar logger do módulo
import logging
logger = logging.getLogger(__name__)

def my_function():
    logger.info("Operação executada", extra={"user_id": user.id})

# ❌ ERRADO: Usar print() em código de produção
def bad_function():
    print("Debug info")  # NÃO FAÇA ISSO
```

### Exceções

**Management Commands** podem usar `self.stdout.write()`:

```python
class Command(BaseCommand):
    def handle(self, *args, **options):
        # ✅ OK para management commands
        self.stdout.write("Processando...")
        self.stdout.write(self.style.SUCCESS("Concluído!"))
```

---

## Frontend (React/JavaScript)

### Logger Condicional

O frontend usa `src/utils/logger.ts` que só loga em desenvolvimento.

```javascript
import logger from '@/utils/logger';

// Em desenvolvimento: logs aparecem no console
// Em produção: logs são suprimidos
logger.debug('Debug info', { data });
logger.log('Operação normal');
logger.warn('Aviso');
logger.error('Erro', error);
logger.api('Request', { url, method });
```

### Implementação

Fonte: `v2/frontend/src/utils/logger.ts`. Os cinco métodos (`log`, `debug`, `warn`,
`error`, `api`) são **todos** condicionados a `import.meta.env.DEV`.

> ⚠️ **Consequência operacional: em produção o frontend não emite nada — nem erros.**
> `logger.error` também é suprimido (`logger.ts:49-55`), e o envio para Sentry está apenas
> comentado como intenção futura. Ao depurar um problema de frontend em produção, **não
> espere achar rastro no console do navegador**: use a aba Network, os logs do `web` no
> backend (correlacionados por `request_id`) e reprodução local com `DEV=true`.

### Boas Práticas

```javascript
// ✅ CORRETO: Usar logger condicional
import logger from '../utils/logger';

async function fetchData() {
  logger.debug('Fetching data...');
  // ...
}

// ❌ ERRADO: Usar console.log direto
async function badFetch() {
  console.log('Fetching data...');  // NÃO FAÇA ISSO
}
```

---

## Dados Sensíveis

### NUNCA logar:
- Tokens de autenticação (JWT, CSRF)
- Senhas (mesmo hasheadas)
- CPF, RG, dados pessoais
- Credenciais de API
- Conteúdo de cookies de sessão

### Logar com cuidado:
- IDs de usuário (OK para debugging)
- Emails (mascarar em produção: `j***@example.com`)
- IPs (considerar LGPD)

---

## Níveis de Log

| Nível | Uso | Exemplo |
|-------|-----|---------|
| DEBUG | Detalhes técnicos para debugging | Payloads de API, queries SQL |
| INFO | Operações normais do sistema | "Usuário X logou", "Evento criado" |
| WARNING | Situações inesperadas mas não críticas | "Cache miss", "Retry em 5s" |
| ERROR | Erros que precisam atenção | Falha de integração, exceções |
| CRITICAL | Falhas graves do sistema | Banco down, serviço indisponível |

---

## Correlation ID (Backend)

O middleware `RequestIDMiddleware` (`config/settings.py:193`) adiciona correlation ID a
todos os logs. Formato real emitido em staging/produção:

```json
{
  "asctime": "2026-07-24 10:00:00,123",
  "levelname": "INFO",
  "name": "apps.core.services.solicitacao_approval",
  "message": "Solicitação aprovada",
  "request_id": "abc123",
  "environment": "production",
  "service": "web"
}
```

Usar `request_id` para rastrear um mesmo request entre `web` e `worker`; usar `service`
para saber de qual container a linha veio.

> **Nota de incidente (2026-07-06):** o formatter exclui explicitamente os atributos
> `request` e `taskName` do LogRecord (`settings.py:646`). Sem isso, cada resposta 4xx/5xx
> serializava o objeto `WSGIRequest` inteiro na linha de log — inundação de disco e
> vazamento de PII. Não remova esse `reserved_attrs`.

---

## Checklist para Code Review

- [ ] Não há `print()` em código de produção (exceto management commands)
- [ ] Não há `console.log()` direto no frontend (usar logger)
- [ ] Dados sensíveis não são logados
- [ ] Nível de log apropriado para a mensagem
- [ ] Mensagens são claras e úteis para debugging

---

## Referências

- [OBSERVABILITY.md](./OBSERVABILITY.md) - Stack de métricas (Prometheus/Grafana)
- [MP2 Structured Logging](./OBSERVABILITY.md#mp2) - Configuração JSON logging
- [PEP 282](https://peps.python.org/pep-0282/) - Logging Python
