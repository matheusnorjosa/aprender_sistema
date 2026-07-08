# shellcheck shell=bash
# lib/confirm.sh — confirmacao de convergencia em localhost (imune ao false-red).
#
# O :9443 tem "false-red" (o PUT chega, prod atualiza, a RESPOSTA nao volta pelo
# firewall). Confirmar em 127.0.0.1 elimina isso: o agente roda NO host. A
# confirmacao e LIVENESS (readyz 200 + version == release), NAO fronteira de
# confianca — a seguranca vem do digest verificado que subiu no PUT.
#
# Host header = PROD_HOST para satisfazer ALLOWED_HOSTS do Django.

# confirm_localhost <release> <backend_host_port> -> 0 se convergiu; !=0 no timeout.
confirm_localhost() {
  local release="$1" port="$2" deadline rdy ver
  local timeout="${CONFIRM_TIMEOUT:-300}" interval="${CONFIRM_INTERVAL:-8}"
  deadline=$(( $(date +%s) + timeout ))
  rdy=""; ver=""
  while [ "$(date +%s)" -lt "$deadline" ]; do
    rdy="$("$CURL_BIN" -s -o /dev/null -w '%{http_code}' --max-time 10 \
        -H "Host: ${PROD_HOST}" "http://127.0.0.1:${port}/api/readyz/" 2>/dev/null || true)"
    ver="$("$CURL_BIN" -s --max-time 10 -H "Host: ${PROD_HOST}" \
        "http://127.0.0.1:${port}/api/version/" 2>/dev/null \
        | "$JQ_BIN" -r '.version // empty' 2>/dev/null || true)"
    if [ "$rdy" = "200" ] && [ "$ver" = "$release" ]; then
      log_info "confirm_ok" "release=${release}"
      return 0
    fi
    sleep "$interval"
  done
  log_error "confirm_timeout" "release=${release}" "last_rdy=${rdy}" "last_ver=${ver}"
  return 1
}
