# shellcheck shell=bash
# lib/fetch.sh — curl endurecido para baixar o ponteiro e a assinatura.
#
# Integridade NAO depende de TLS (tudo e verificado por assinatura depois); o
# endurecimento aqui e para reduzir superficie: https-only, sem seguir redirect
# (nao passamos -L => redirect cross-host nao acontece), timeout, tamanho maximo
# (o ponteiro e pequeno; corta payload gigante hostil), e allowlist de host.

# Prefixo de host permitido para o ponteiro (override em testes).
: "${POINTER_HOST_PREFIX:=https://raw.githubusercontent.com/}"

# fetch_url <url> <dest_file> -> 0 ok; 2 host negado; !=0 erro de rede/http.
fetch_url() {
  local url="$1" dest="$2"
  case "$url" in
    "${POINTER_HOST_PREFIX}"*) : ;;
    *) log_error "fetch_host_denied" "url=${url}"; return 2 ;;
  esac
  local -a opts=(
    -fsS --proto '=https' --tlsv1.2
    --max-time "${FETCH_MAX_TIME:-30}"
    --max-filesize "${FETCH_MAX_BYTES:-65536}"
    -o "$dest"
  )
  # Opcional: TLS pubkey pinning para raw.githubusercontent.com (defesa extra anti-MITM).
  [ -n "${FETCH_PINNEDPUBKEY:-}" ] && opts+=(--pinnedpubkey "$FETCH_PINNEDPUBKEY")
  "$CURL_BIN" "${opts[@]}" "$url"
}
