## Contexto
Runtime de containers ainda permite baseline abaixo do recomendado (uso de root e poucas restricoes de privilegio/filesystem).

## Objetivo
Aplicar hardening de execucao para reduzir impacto de compromissos no container.

## Plano de implementacao
1. Definir `USER` nao-root nas imagens de producao (`backend` e `frontend`).
2. Ativar `no-new-privileges` nos servicos do compose.
3. Habilitar `read_only: true` com `tmpfs` apenas onde necessario para escrita.
4. Aplicar `cap_drop: [ALL]` e adicionar somente capacidades estritamente necessarias.
5. Revisar mounts e permissoes para evitar escrita ampla no host.
6. Validar compatibilidade operacional (logs, uploads, sockets, arquivos temporarios).

## Resultado esperado dos testes
- Containers iniciam e rodam como usuario nao-root.
- Escritas fora dos caminhos permitidos falham como esperado.
- Scans/politicas de runtime passam para non-root, read-only e cap-drop.

## Criterios de aceite
- Compose e Dockerfiles com baseline hardening aplicado e testado.
- Evidencia de execucao sem root anexada na PR.
- Checklist de runtime seguro atualizado no runbook.

## Referencias
- OWASP Docker Security Cheat Sheet
- Docker Engine Security
