#!/usr/bin/env bash
set -euo pipefail
cd "$(git rev-parse --show-toplevel)"

is_up() {
  # considera Up se o serviço web aparece como "Up"
  docker compose ps --status running web 2>/dev/null | grep -qi "web"
}

run_in_web() {
  docker compose exec -T web "$@"
}

cmd="${1:-check}"

if ! is_up; then
  echo "[pre-commit] container 'web' não está 'Up'; pulando hooks Django."
  # para não travar commits quando o dev está offline
  exit 0
fi

case "$cmd" in
  check)
    run_in_web python manage.py check
    ;;
  makemigrations)
    run_in_web python manage.py makemigrations --check --dry-run
    ;;
  showmigrations)
    run_in_web python manage.py showmigrations
    ;;
  *)
    echo "uso: $0 {check|makemigrations|showmigrations}" >&2
    exit 2
    ;;
esac
