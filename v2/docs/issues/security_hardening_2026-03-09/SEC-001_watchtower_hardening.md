## Contexto
O servico `watchtower` esta com superficie de controle maior que o necessario quando a API HTTP fica acessivel fora da rede administrativa e com `docker.sock` montado. Em caso de exposicao indevida, isso vira vetor de takeover operacional.

## Objetivo
Eliminar exposicao externa do plano de controle de atualizacao de containers, mantendo apenas operacao autenticada e interna.

## Plano de implementacao
1. Remover `ports` publicos do servico `watchtower` em `v2/infra/docker-compose.prod.yml`.
2. Colocar o servico em rede interna exclusiva de administracao (sem roteamento externo).
3. Tornar `WATCHTOWER_HTTP_API_TOKEN` obrigatorio e carregado via secret file.
4. Bloquear acesso no host (firewall/ACL) para portas administrativas nao necessarias.
5. Avaliar migracao para execucao `--run-once` por job autenticado interno e remover API HTTP continua.
6. Atualizar runbook operacional com procedimento seguro de atualizacao.

## Resultado esperado dos testes
- `curl` externo para endpoint do watchtower retorna `timeout` ou `connection refused`.
- Requisicao interna com token valido executa acao esperada.
- Requisicao interna sem token ou token invalido retorna `401/403`.
- Port scan externo nao encontra endpoint administrativo publicado.

## Criterios de aceite
- Nenhuma porta administrativa do watchtower publicada externamente.
- Token obrigatorio em producao validado em teste de fumaca.
- Evidencia de bloqueio de rede anexada na PR (compose + firewall/ACL + teste).

## Referencias
- OWASP Docker Security Cheat Sheet
- Docker Engine Security (daemon attack surface)
