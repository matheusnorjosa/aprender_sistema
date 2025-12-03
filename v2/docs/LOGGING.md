# Guia de Logging - AS v2

**Data**: 2025-12-03
**Status**: Ativo
**Issue**: #227

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

A configuração está em `config/settings.py`:

- **Development**: Logs legíveis no console
- **Staging/Production**: Logs JSON estruturados com correlation ID

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

O frontend usa `src/utils/logger.js` que só loga em desenvolvimento.

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

```javascript
// src/utils/logger.js
const isDev = import.meta.env.DEV;

const logger = {
  log: (...args) => isDev && console.log(...args),
  debug: (...args) => isDev && console.log('[DEBUG]', ...args),
  warn: (...args) => isDev && console.warn(...args),
  error: (...args) => isDev && console.error(...args),
  api: (label, data) => isDev && console.log(`[API] ${label}:`, data),
};

export default logger;
```

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

O middleware `RequestIDMiddleware` adiciona correlation ID a todos os logs:

```json
{
  "timestamp": "2025-12-03T10:00:00",
  "level": "INFO",
  "request_id": "abc123",
  "message": "Solicitação aprovada"
}
```

Usar para rastrear requests através de múltiplos serviços.

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
