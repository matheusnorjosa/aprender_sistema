#!/usr/bin/env bash
# break-glass.sh — deploy manual de emergencia (quando o :9443 estiver fechado, Fase 4).
#
# NAO e um bypass da verificacao: reusa a MESMA cadeia (verifica ponteiro/imagens,
# checa selo, compose pinado, backup) e o MESMO lock do applier. A unica diferenca
# e o gatilho: um operador humano (via SSH + break-glass), em vez do timer.
#
# Uso (como usuario aprender-applier, dentro de um SSH tunnel para o Portainer):
#   sudo -u aprender-applier /opt/aprender-deployer/current/break-glass.sh
#
# Requer: handoff ja escrito pelo deployer OU baixar o ponteiro on-demand. Por
# seguranca, este script chama o reconcile do deployer (fetch+verify+handoff) e
# depois o apply do applier — reusando 100% da logica, sem duplicar verificacao.
#
# ADR-018 · issue #1516 (Fase 4) · blueprint §B
set -euo pipefail
DIR="$(unset CDPATH; cd -- "$(dirname -- "$0")" && pwd -P)"

echo "break-glass: reconcile (fetch+verify) -> apply (re-verify+PUT+confirm)"
echo "ATENCAO: usa a mesma verificacao; NAO burla o gate. Registrar no runbook quem/por que."

# 1) força um reconcile (deployer) para (re)escrever o handoff verificado
"$DIR/reconcile.sh"

# 2) aplica (applier) — re-verifica tudo e faz o PUT via localhost:9443
exec "$DIR/apply.sh"
