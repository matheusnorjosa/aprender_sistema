# Plano de Hardening de Cyberseguranca (2026-03-09)

## 1) Objetivo
Este plano consolida as fragilidades identificadas nas analises de codigo, configuracao e testes praticos (incluindo tentativas via console do navegador) e define uma remediacao definitiva, com criterios de aceite e resultados esperados de testes.

## 2) Escopo consolidado
- Backend Django/DRF (`v2/backend`)
- Frontend React (`v2/frontend`)
- Infra Docker/Nginx/Redis/Celery (`v2/infra`)
- CI/CD GitHub Actions (`.github/workflows`)

## 3) Riscos e trilhas de correcao

### Trilha A - Plano de controle de containers exposto (Critico)
Problema atual:
- Watchtower com API HTTP habilitada/exposta e com socket Docker montado.
- Isso aumenta risco de takeover operacional se houver exposicao indevida.

Correcao definitiva:
1. Remover publicacao de porta da API do Watchtower para internet.
2. Restringir endpoint de gestao a rede interna privada (sem `ports` publicos; usar network interna).
3. Manter/forcar token forte (`WATCHTOWER_HTTP_API_TOKEN`) vindo de secret file.
4. Avaliar substituir modo HTTP API por execucao `--run-once` via job interno autenticado.
5. Aplicar firewall/ACL de host para negar acesso externo a endpoints de gestao.

Implementacao:
- Arquivo principal: `v2/infra/docker-compose.prod.yml`.
- Ajustar servico `watchtower` para sem exposicao externa e com segredo obrigatorio.
- Atualizar runbook de operacao/atualizacao segura.

Testes esperados apos implementacao:
- `curl` externo para endpoint HTTP API retorna timeout/connection refused.
- Atualizacao legitima interna com token valido funciona.
- Sem token ou token invalido: `401/403`.
- Scan de portas em host nao mostra endpoint de gestao exposto.

### Trilha B - Redis/Celery sem hardening uniforme (Alto)
Problema atual:
- Inconsistencia de auth entre cache e broker Celery.
- Risco de abuso em rede interna se Redis ficar acessivel sem autenticacao/TLS.

Correcao definitiva:
1. Padronizar URL unica para Redis com senha obrigatoria no cache/sessions/Celery.
2. Forcar TLS (`rediss://`) quando ambiente suportar.
3. Restringir bind/rede do Redis para subnet interna.
4. Se possivel, migrar para ACL Redis (usuarios dedicados por funcao: cache, broker, results).

Implementacao:
- `v2/backend/config/settings.py`: consolidar `REDIS_URL` e remover caminhos sem senha.
- `v2/infra/.env.production`: adicionar variaveis obrigatorias (`REDIS_PASSWORD`, opcionalmente certs TLS).
- `v2/infra/redis/redis.conf`: auth/protected mode/network hardening.

Testes esperados apos implementacao:
- Aplicacao sobe com Redis autenticado.
- Tentativa de conexao sem senha falha (`NOAUTH`/erro de auth).
- Celery workers processam tasks normalmente com URL autenticada.
- Teste de conectividade com TLS passa onde habilitado.

### Trilha C - Vazamento de detalhes de erro em respostas (Medio)
Problema atual:
- Alguns endpoints retornam `str(e)` para cliente.
- Facilita recon e engenharia de ataque.

Correcao definitiva:
1. Padronizar respostas 4xx/5xx com mensagem generica e codigo interno de erro.
2. Logar detalhes apenas server-side (com request id/correlation id).
3. Revisar handlers globais para impedir leak de stack/exception text em producao.

Implementacao:
- Revisar views que retornam `str(e)`.
- Criar helper central de erro padronizado (`code`, `detail` generico).
- Atualizar testes de contrato de erro.

Testes esperados apos implementacao:
- Falhas de backend retornam payload padrao sem texto interno.
- Logs internos mantem detalhe tecnico para troubleshooting.
- Testes garantem ausencia de substrings sensiveis (`Traceback`, nomes de classe/driver/SQL).

### Trilha D - CSP permissiva (`unsafe-inline`/`unsafe-eval`) (Medio)
Problema atual:
- Politica atual reduz efetividade contra XSS.

Correcao definitiva:
1. Migrar para CSP estrita com nonce/hash para scripts legitimos.
2. Remover `unsafe-eval`; remover `unsafe-inline` de `script-src`.
3. Operar em modo `Report-Only` por janela curta e depois aplicar modo enforcing.

Implementacao:
- `v2/backend/apps/core/middleware_security.py`.
- Ajustes no frontend para eliminar inline scripts/event handlers onde houver.
- Endpoint de coleta de relatorios CSP (ou integracao com SIEM).

Testes esperados apos implementacao:
- Testes E2E passam sem quebrar funcionalidades.
- Injecoes inline/eval bloqueadas no browser.
- Relatorio CSP mostra queda progressiva de violacoes ate nivel aceitavel.

### Trilha E - Endpoints de gestao/observabilidade/documentacao expostos (Medio)
Problema atual:
- `readyz/metrics/schema/docs/redoc` podem ampliar superficie de recon.

Correcao definitiva:
1. Separar endpoints publicos minimos de probe de infraestrutura (liveness/readiness simplificados).
2. Proteger metrics/docs/schema com auth forte + allowlist de rede + rate-limit.
3. Opcional: mover observabilidade para porta/rede dedicada de administracao.

Implementacao:
- `v2/backend/config/urls.py` e configuracao de roteamento/reverse-proxy.
- `drf-spectacular`: `SERVE_PERMISSIONS` restritivas em producao.

Testes esperados apos implementacao:
- Usuario nao autenticado recebe `401/403` em docs/schema/metrics.
- Probes internos continuam funcionando para orquestrador.
- Testes de permissao por perfil confirmam isolamento.

### Trilha F - Hardening de runtime de containers incompleto (Alto)
Problema atual:
- Imagens sem `USER` dedicado e sem restricoes adicionais.

Correcao definitiva:
1. Definir `USER` nao-root em todas as imagens de app.
2. Ativar `no-new-privileges`, `read_only`, `tmpfs` para caminhos de escrita necessarios.
3. Reduzir capabilities (drop all + add minimo necessario).
4. Tornar filesystem de runtime minimamente mutavel.

Implementacao:
- `v2/infra/Dockerfile.prod`, `v2/frontend/Dockerfile.prod`, `docker-compose.prod.yml`.

Testes esperados apos implementacao:
- Containers sobem e funcionam como usuario nao-root.
- Escrita indevida fora de paths permitidos falha.
- Security scans de compose/runtime passam politicas minimas (cap drop, read-only, non-root).

### Trilha G - CSV Formula Injection em exportacoes (Medio)
Problema atual:
- Campos exportados podem iniciar com caracteres de formula.

Correcao definitiva:
1. Sanitizar cada celula exportada para contextos CSV de planilha.
2. Aplicar estrategia padrao para valores iniciando em `=`, `+`, `-`, `@`, TAB, CR, LF.
3. Cobrir todos os pontos de export backend/frontend.

Implementacao:
- Centralizar helper `sanitize_for_csv_spreadsheet(value)`.
- Aplicar nos endpoints de export.

Testes esperados apos implementacao:
- Fixtures maliciosas sao exportadas sem execucao de formula.
- Testes unitarios validam prefix/sanitizacao para todos os caracteres de risco.
- Teste manual em Excel/LibreOffice confirma abertura segura.

### Trilha H - Swagger UI com `persistAuthorization` habilitado (Medio/Baixo)
Problema atual:
- Persistencia de credenciais no browser aumenta risco operacional em maquinas compartilhadas.

Correcao definitiva:
1. Desabilitar `persistAuthorization` em producao.
2. Exigir auth para acesso ao Swagger/Redoc em producao.
3. Definir timeout de sessao e orientacao operacional para ambientes administrativos.

Implementacao:
- `v2/backend/config/settings.py` (`SPECTACULAR_SETTINGS`).
- Politica de acesso por ambiente (dev vs staging/prod).

Testes esperados apos implementacao:
- Reload do Swagger limpa credenciais em producao.
- Sem auth: docs indisponivel (`401/403`).
- Com auth: funcionamento normal de exploracao controlada.

### Trilha I - Politica CORS/CSRF em producao precisa de minimizacao (Medio/Baixo)
Problema atual:
- `CORS_ALLOW_CREDENTIALS=True` e listas amplas de origem exigem governanca rigorosa em prod.

Correcao definitiva:
1. Separar configuracoes por ambiente (dev amplo, prod restrito).
2. Em producao, permitir apenas origens explicitas e necessarias.
3. Revisao periodica automatizada de origem confiada (drift check em CI).

Implementacao:
- `v2/backend/config/settings.py` + `.env.production`.
- Validacao de env no startup/CI para impedir wildcard com credentials.

Testes esperados apos implementacao:
- Origem permitida recebe headers corretos.
- Origem nao permitida falha sem `Access-Control-Allow-Origin`.
- Preflight de origem invalida bloqueado.

### Trilha J - Regressao de controle de acesso via client-side (Baixo, preventivo)
Contexto:
- O PoC de escalacao via `_auth/localStorage` NAO foi reproduzido no estado atual.
- Ainda assim, deve existir teste de regressao permanente para evitar reintroducao.

Correcao definitiva (preventiva):
1. Criar testes E2E de tampering (`localStorage`, fake JWT, flags de perfil) validando que API continua `403`.
2. Adicionar gate de CI de seguranca para esses cenarios.
3. Manter regra arquitetural: autorizacao somente server-side.

Implementacao:
- Suite Playwright de seguranca dedicada.
- Documentar padrao no guia de contribuicao.

Testes esperados apos implementacao:
- Injetar `_auth/perfil=ADMIN` nao libera menu nem endpoint admin.
- Endpoints sensiveis permanecem protegidos por RBAC server-side.

## 4) Ordem de execucao recomendada
- Fase P0 (0-7 dias): Trilhas A, B, C.
- Fase P1 (8-21 dias): Trilhas D, E, F.
- Fase P2 (22-35 dias): Trilhas G, H, I, J.

## 5) Criterios globais de conclusao
- Nenhum endpoint administrativo/operacional exposto sem controle.
- Nenhuma autorizacao efetiva dependente de estado client-side.
- Nenhuma resposta de erro em producao com detalhe tecnico interno.
- Containers e dependencias rodando com baseline de hardening definida.
- Testes de seguranca automatizados no CI com bloqueio de regressao.

## 6) Referencias de melhores praticas
- OWASP Docker Security Cheat Sheet: https://cheatsheetseries.owasp.org/cheatsheets/Docker_Security_Cheat_Sheet.html
- Docker Engine Security (daemon attack surface): https://docs.docker.com/engine/security/
- Redis Security: https://redis.io/docs/latest/operate/oss_and_stack/management/security/
- Celery + Redis broker URL/auth: https://docs.celeryq.dev/en/stable/getting-started/backends-and-brokers/redis.html
- OWASP Error Handling Cheat Sheet: https://cheatsheetseries.owasp.org/cheatsheets/Error_Handling_Cheat_Sheet.html
- OWASP CSP Cheat Sheet: https://cheatsheetseries.owasp.org/cheatsheets/Content_Security_Policy_Cheat_Sheet.html
- OWASP REST Security Cheat Sheet (management endpoints): https://cheatsheetseries.owasp.org/cheatsheets/REST_Security_Cheat_Sheet.html
- OWASP Authorization Cheat Sheet: https://cheatsheetseries.owasp.org/cheatsheets/Authorization_Cheat_Sheet.html
- OWASP CSV Injection: https://owasp.org/www-community/attacks/CSV_Injection
- Swagger UI configuration (`persistAuthorization`): https://swagger.io/docs/open-source-tools/swagger-ui/usage/configuration/
- drf-spectacular settings (`SERVE_PERMISSIONS`): https://drf-spectacular.readthedocs.io/en/latest/settings.html
- MDN CORS credentials guidance: https://developer.mozilla.org/en-US/docs/Web/HTTP/Guides/CORS/Errors/CORSNotSupportingCredentials
