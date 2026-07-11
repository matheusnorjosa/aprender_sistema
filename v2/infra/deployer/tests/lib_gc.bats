#!/usr/bin/env bats
# lib_gc.bats — retencao de imagens pos-deploy (lib/gc.sh). Deterministico, sem rede.
#
# Deleta por REFERENCIA (repo:tag e repo@digest), nao por Id: o pin repo:tag@digest da
# duas refs por imagem e um `docker rmi` por Id recusaria 409. Estes testes provam que
# ambas as refs saem, que a imagem EM USO nunca e tocada, o anti-injecao/scoping, e que
# nada aborta (best-effort, ate sob set -e).
#
# Fixture:
#   backend  K=0..4: RepoTags=[BE:bK], RepoDigests=[BE@sha256:h64(K)],     Created=100+K, em uso=h64(4)
#   frontend K=0..3: RepoTags=[FE:fK], RepoDigests=[FE@sha256:h64(100+K)], Created=100+K, em uso=h64(103)

load helper

setup()    { setup_sandbox; _gc_setup; }
teardown() { teardown_sandbox; }

# -- fixtures ---------------------------------------------------------------------

_h64() { printf '%064x' "$1"; }

_gc_setup() {
  export P_BACKEND_REPO="norjosamatheus/aprender-backend"
  export P_FRONTEND_REPO="norjosamatheus/aprender-frontend"
  export P_BACKEND_DIGEST="sha256:$(_h64 4)"     # backend em uso (o mais novo)
  export P_FRONTEND_DIGEST="sha256:$(_h64 103)"  # frontend em uso (o mais novo)

  export PORTAINER_BASE="https://127.0.0.1:9443" PORTAINER_ENDPOINT_ID="3"
  export PORTAINER_CURLRC="$SANDBOX/curlrc"; printf 'header = "X-API-KEY: ptr_test"\n' > "$PORTAINER_CURLRC"

  export MOCK_IMAGES_FILE="$SANDBOX/images.json"
  export MOCK_DELETED_FILE="$SANDBOX/deleted.txt"; : > "$MOCK_DELETED_FILE"
  export MOCK_DELETE_CODE="${MOCK_DELETE_CODE:-200}"

  _mk "$SANDBOX/mock_curl" '#!/usr/bin/env bash
url=""; method=GET; want_code=0; prev=""
for a in "$@"; do
  case "$prev" in -X) method="$a";; esac
  case "$a" in http://*|https://*) url="$a";; -w) want_code=1;; esac
  prev="$a"
done
case "$url" in
  */docker/images/json)
     cat "$MOCK_IMAGES_FILE"; exit $? ;;
  */docker/images/*)
     if [ "$method" = DELETE ]; then
       ref="${url##*/docker/images/}"; ref="${ref%%\?*}"
       printf "%s\n" "$ref" >> "$MOCK_DELETED_FILE"
       [ "$want_code" = 1 ] && printf "%s" "${MOCK_DELETE_CODE:-200}"
       exit 0
     fi ;;
esac
exit 1'
  export CURL_BIN="$SANDBOX/mock_curl"
}

# _img <repo> <tag> <created> <n>  -> RepoTags=[repo:tag], RepoDigests=[repo@sha256:h64(n)]
_img() {
  printf '{"Id":"sha256:%s","Created":%s,"RepoTags":["%s:%s"],"RepoDigests":["%s@sha256:%s"]}' \
    "$(_h64 "$4")" "$3" "$1" "$2" "$1" "$(_h64 "$4")"
}

_write_default() {
  local b f
  b="$(_img "$P_BACKEND_REPO" b0 100 0)"
  b="$b,$(_img "$P_BACKEND_REPO" b1 101 1)"
  b="$b,$(_img "$P_BACKEND_REPO" b2 102 2)"
  b="$b,$(_img "$P_BACKEND_REPO" b3 103 3)"
  b="$b,$(_img "$P_BACKEND_REPO" b4 104 4)"
  f="$(_img "$P_FRONTEND_REPO" f0 100 100)"
  f="$f,$(_img "$P_FRONTEND_REPO" f1 101 101)"
  f="$f,$(_img "$P_FRONTEND_REPO" f2 102 102)"
  f="$f,$(_img "$P_FRONTEND_REPO" f3 103 103)"
  printf '[%s,%s]' "$b" "$f" > "$MOCK_IMAGES_FILE"
}

_has()   { grep -qF "$1" "$MOCK_DELETED_FILE"; }
_count() { if [ -s "$MOCK_DELETED_FILE" ]; then grep -c . "$MOCK_DELETED_FILE"; else printf 0; fi; }

# -- testes -----------------------------------------------------------------------

@test "keep=3: deleta AMBAS as refs (tag+digest) das antigas; preserva running/kept" {
  export IMAGE_GC_KEEP=3
  _write_default
  run gc_run
  [ "$status" -eq 0 ]
  _has "$P_BACKEND_REPO:b0"; _has "$P_BACKEND_REPO@sha256:$(_h64 0)"   # backend Created 100
  _has "$P_BACKEND_REPO:b1"; _has "$P_BACKEND_REPO@sha256:$(_h64 1)"   # backend Created 101
  _has "$P_FRONTEND_REPO:f0"; _has "$P_FRONTEND_REPO@sha256:$(_h64 100)"  # frontend Created 100
  ! _has "$P_BACKEND_REPO:b4"; ! _has "$P_BACKEND_REPO@sha256:$(_h64 4)"  # running/kept: intacto
  ! _has "$P_FRONTEND_REPO:f3"
  [ "$(_count)" -eq 6 ]
}

@test "NUNCA toca a imagem em uso, mesmo sendo a mais antiga (nenhuma ref)" {
  export P_BACKEND_DIGEST="sha256:$(_h64 0)"   # backend em uso = o MAIS ANTIGO (Created 100)
  export IMAGE_GC_KEEP=3
  _write_default
  run gc_run
  [ "$status" -eq 0 ]
  ! _has "$P_BACKEND_REPO:b0"; ! _has "$P_BACKEND_REPO@sha256:$(_h64 0)"  # em uso: nenhuma ref sai
  _has "$P_BACKEND_REPO:b1";  _has "$P_BACKEND_REPO@sha256:$(_h64 1)"     # o outro antigo: removido
}

@test "DELETE 409 (em uso) nao aborta: gc_run retorna 0" {
  export IMAGE_GC_KEEP=3 MOCK_DELETE_CODE=409
  _write_default
  run gc_run
  [ "$status" -eq 0 ]
}

@test "best-effort sob set -e: 409 nao derruba o shell" {
  export IMAGE_GC_KEEP=3 MOCK_DELETE_CODE=409
  _write_default
  run bash -c 'set -euo pipefail; . "$DEPLOYER_HOME/lib/common.sh"; gc_run; echo "RC=$?"'
  [ "$status" -eq 0 ]
  [[ "$output" == *"RC=0"* ]]
}

@test "falha ao listar nao aborta: rc=0 e nada removido" {
  export IMAGE_GC_KEEP=3
  rm -f "$MOCK_IMAGES_FILE"
  run gc_run
  [ "$status" -eq 0 ]
  [ "$(_count)" -eq 0 ]
}

@test "resposta nao-array nao aborta e nada e removido" {
  export IMAGE_GC_KEEP=3
  printf 'not-an-array' > "$MOCK_IMAGES_FILE"
  run gc_run
  [ "$status" -eq 0 ]
  [ "$(_count)" -eq 0 ]
}

@test "referencia com injecao no tag e recusada: nenhum DELETE emitido" {
  export IMAGE_GC_KEEP=1
  export P_BACKEND_DIGEST="sha256:$(_h64 999)"
  local good bad
  good="$(_img "$P_BACKEND_REPO" good 200 50)"
  bad='{"Id":"sha256:'"$(_h64 100)"'","Created":100,"RepoTags":["'"$P_BACKEND_REPO"':v1; rm -rf /"],"RepoDigests":[]}'
  printf '[%s,%s]' "$good" "$bad" > "$MOCK_IMAGES_FILE"
  run gc_run
  [ "$status" -eq 0 ]
  [ "$(_count)" -eq 0 ]
}

@test "ref de repo estranho na mesma imagem e ignorada (scoping)" {
  export IMAGE_GC_KEEP=1
  export P_BACKEND_DIGEST="sha256:$(_h64 999)"
  local new old
  new="$(_img "$P_BACKEND_REPO" bnew 300 60)"
  old='{"Id":"sha256:'"$(_h64 61)"'","Created":100,"RepoTags":["'"$P_BACKEND_REPO"':bold","evilcorp/x:latest"],"RepoDigests":["'"$P_BACKEND_REPO"'@sha256:'"$(_h64 61)"'"]}'
  printf '[%s,%s]' "$new" "$old" > "$MOCK_IMAGES_FILE"
  run gc_run
  [ "$status" -eq 0 ]
  _has "$P_BACKEND_REPO:bold"; _has "$P_BACKEND_REPO@sha256:$(_h64 61)"
  ! _has "evilcorp/x:latest"
}

@test "IMAGE_GC_ENABLED=0 desliga: nada removido" {
  export IMAGE_GC_ENABLED=0 IMAGE_GC_KEEP=3
  _write_default
  run gc_run
  [ "$status" -eq 0 ]
  [ "$(_count)" -eq 0 ]
}

@test "IMAGE_GC_KEEP=0 e invalido (min 1): protege prod, nada removido" {
  export IMAGE_GC_KEEP=0
  _write_default
  run gc_run
  [ "$status" -eq 0 ]
  [ "$(_count)" -eq 0 ]
}

@test "keep >= total: nada a remover" {
  export IMAGE_GC_KEEP=50
  _write_default
  run gc_run
  [ "$status" -eq 0 ]
  [ "$(_count)" -eq 0 ]
}

@test "IMAGE_GC_BUDGET=0: para antes de qualquer delete (deadline no passado)" {
  export IMAGE_GC_KEEP=3 IMAGE_GC_BUDGET=0
  _write_default
  run gc_run
  [ "$status" -eq 0 ]
  [ "$(_count)" -eq 0 ]
}

@test "gc_delete_one recusa ref multi-linha (grep casa por-linha; defense-in-depth)" {
  local mlref
  mlref="$P_BACKEND_REPO:v1
?force=true&x=y"
  run gc_delete_one "$P_BACKEND_REPO" "$mlref"
  [ "$status" -ne 0 ]
  [ "$(_count)" -eq 0 ]
}

@test "gc_delete_one aceita ref valida por referencia e emite 1 DELETE" {
  run gc_delete_one "$P_BACKEND_REPO" "$P_BACKEND_REPO:vok"
  [ "$status" -eq 0 ]
  _has "$P_BACKEND_REPO:vok"
  [ "$(_count)" -eq 1 ]
}
