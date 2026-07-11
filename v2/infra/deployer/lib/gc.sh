# shellcheck shell=bash
# lib/gc.sh — retencao de imagens pos-deploy (ADR-018).
#
# Depois de um deploy CONFIRMADO (selo avancado), remove imagens ANTIGAS dos repos
# aprender-* via a API do Portainer (o MESMO token do applier; SEM socket docker),
# mantendo as IMAGE_GC_KEEP mais novas por repo. Motivo: cada release baixa uma
# imagem nova por digest e a anterior fica no store para sempre -> o disco da VM01
# (60GB) enche. O fluxo pull-based nunca teve GC (issue #1548).
#
# Por REFERENCIA, nao por Id: o compose pina `repo:${IMAGE_TAG}@${DIGEST}` (Opcao B),
# entao cada imagem carrega DUAS referencias (um RepoTag e um RepoDigest). `docker rmi`
# por Id com force=false RECUSA (409) uma imagem com >1 referencia — o GC nao limparia
# nada. Removemos cada referencia (RepoTag/RepoDigest do repo); a imagem e recuperada
# quando a ULTIMA referencia sai. force=false continua fail-safe (o delete final de uma
# imagem em uso por container devolve 409).
#
# Invariantes de seguranca (todas exercitadas em tests/lib_gc.bats):
#   - best-effort: NUNCA aborta um deploy (toda falha -> log + return 0). E chamado
#     DEPOIS do selo; um erro aqui nao pode reverter um deploy ja confirmado.
#   - NUNCA toca a imagem EM USO: exclusao explicita do running digest (nunca emitimos
#     nenhuma referencia dela) + force=false. Duas travas independentes.
#   - keep >= 1 SEMPRE: 0 nao protegeria nada; a versao em producao sempre fica.
#   - deadline de parede (IMAGE_GC_BUDGET): o GC nunca gasta mais que isso, bem abaixo
#     do TimeoutStartSec do systemd. Para cedo e LOGA (sem corte silencioso).
#   - anti-injecao em DUAS camadas: a referencia (a) tem de comecar com o repo esperado
#     (allowlist) e (b) casar um charset seguro (sem metacaractere de shell/URL) antes
#     de entrar na URL do DELETE.
#   - as imagens locais sao CACHE: o registry guarda todo digest e o deploy repulla
#     (RepullImageAndRedeploy:true), entao remover local NAO quebra rollback.

: "${IMAGE_GC_ENABLED:=1}"
: "${IMAGE_GC_KEEP:=3}"
: "${IMAGE_GC_BUDGET:=120}"

# gc_candidates <images_json> <repo> <keep> <running_digest> -> referencias a remover
# (uma por linha). Seleciona as imagens do <repo>, ordena por Created (desc), MANTEM as
# <keep> mais novas, EXCLUI a que carrega o <running_digest>, e emite cada RepoTag/
# RepoDigest do <repo> das restantes.
gc_candidates() {
  local images="$1" repo="$2" keep="$3" running="$4"
  "$JQ_BIN" -r --arg repo "$repo" --argjson keep "$keep" --arg running "$running" '
    [ .[]
      | select(
          ((.RepoTags    // []) | any(startswith($repo + ":")))
          or ((.RepoDigests // []) | any(startswith($repo + "@")))
        )
    ]
    | sort_by(.Created) | reverse
    | .[$keep:]
    | .[]
    | select(((.RepoDigests // []) | any(. == ($repo + "@" + $running))) | not)
    | ((.RepoTags // []) + (.RepoDigests // []))[]
    | select(startswith($repo + ":") or startswith($repo + "@"))
  ' <<<"$images" 2>/dev/null || true
}

# gc_delete_one <repo> <ref> -> 0 se removeu; !=0 caso contrario. Sempre NAO-fatal.
gc_delete_one() {
  local repo="$1" ref="$2" http
  # 0a trava: rejeita ref vazia / multi-linha / com controle. A 2a trava (grep -Eq) casa
  # POR LINHA, entao sem isto uma ref forjada tipo `repo:tag\n?force=true` passaria (linha 1
  # valida) e o resto entraria na URL. Um daemon legitimo nunca emite isso (a gramatica de
  # referencia do Docker proibe \n), mas a validacao nao deve depender do formato do caller.
  case "$ref" in
    ''|*[$'\n\r']*) log_warn "gc_ref_invalid"; return 1 ;;
  esac
  # 1a trava: a referencia pertence ao repo esperado (allowlist da identity.env).
  case "$ref" in
    "${repo}:"*|"${repo}@"*) : ;;
    *) log_warn "gc_ref_foreign" "ref=${ref}"; return 1 ;;
  esac
  # 2a trava: charset seguro (sem metacaractere de shell/URL) -> anti-injecao na URL.
  printf '%s' "$ref" \
    | grep -Eq '^[A-Za-z0-9][A-Za-z0-9._/-]*(:[A-Za-z0-9][A-Za-z0-9._-]*|@sha256:[0-9a-f]{64})$' \
    || { log_warn "gc_bad_ref" "ref=${ref}"; return 1; }
  http="$(portainer_delete_image "$ref")" \
    || { log_warn "gc_delete_err" "ref=${ref}"; return 1; }
  case "$http" in
    2*)  log_audit "gc_removed"     "ref=${ref}" "http=${http}"; return 0 ;;
    409) log_info  "gc_in_use"      "ref=${ref}"; return 1 ;;   # em uso por container: seguro
    404) log_info  "gc_absent"      "ref=${ref}"; return 1 ;;   # ja removida
    *)   log_warn  "gc_delete_http" "ref=${ref}" "http=${http}"; return 1 ;;
  esac
}

# gc_run -> executa a retencao. Best-effort; retorna 0 SEMPRE (chamado apos o selo).
gc_run() {
  [ "${IMAGE_GC_ENABLED:-1}" = "1" ] || { log_info "gc_disabled"; return 0; }

  local keep="${IMAGE_GC_KEEP:-3}"
  case "$keep" in ''|*[!0-9]*) log_warn "gc_keep_bad" "keep=${keep}"; return 0 ;; esac
  [ "$keep" -ge 1 ] || { log_warn "gc_keep_lt1" "keep=${keep}"; return 0; }  # min 1: prod nunca sai

  local budget="${IMAGE_GC_BUDGET:-120}"
  case "$budget" in ''|*[!0-9]*) budget=120 ;; esac
  local deadline; deadline=$(( $(date +%s 2>/dev/null || echo 0) + budget ))

  local images
  images="$(portainer_list_images)" || { log_warn "gc_list_failed"; return 0; }
  "$JQ_BIN" -e 'type=="array"' >/dev/null 2>&1 <<<"$images" \
    || { log_warn "gc_list_not_array"; return 0; }

  local pair repo digest ref total=0 removed=0 stopped=0
  for pair in "${P_BACKEND_REPO:-}|${P_BACKEND_DIGEST:-}" \
              "${P_FRONTEND_REPO:-}|${P_FRONTEND_DIGEST:-}"; do
    repo="${pair%%|*}"; digest="${pair##*|}"
    [ -n "$repo" ] && [ -n "$digest" ] || { log_warn "gc_repo_skip" "repo=${repo}"; continue; }
    while IFS= read -r ref; do
      [ -n "$ref" ] || continue
      if [ "$(date +%s 2>/dev/null || echo 0)" -ge "$deadline" ]; then stopped=1; break; fi
      total=$((total + 1))
      gc_delete_one "$repo" "$ref" && removed=$((removed + 1)) || true
    done < <(gc_candidates "$images" "$repo" "$keep" "$digest")
    [ "$stopped" -eq 1 ] && break
  done

  [ "$stopped" -eq 1 ] && log_warn "gc_budget_exhausted" "budget=${budget}" "refs_deleted=${removed}"
  log_info "gc_done" "keep=${keep}" "refs_seen=${total}" "refs_deleted=${removed}" "stopped=${stopped}"
  return 0
}
