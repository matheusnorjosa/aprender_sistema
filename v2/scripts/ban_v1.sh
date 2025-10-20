#!/usr/bin/env bash
set -euo pipefail

PROJECT=aprendersistema

if ! command -v docker >/dev/null 2>&1; then
  echo "docker command not found" >&2
  exit 1
fi

echo "==> Containers (project=$PROJECT)"
ids=$(docker ps -aq -f "label=com.docker.compose.project=${PROJECT}")
if [ -n "$ids" ]; then
  docker rm -f $ids
else
  echo "Nenhum container legado encontrado."
fi

echo "==> Redes"
networks=$(docker network ls -q -f "label=com.docker.compose.project=${PROJECT}")
if [ -n "$networks" ]; then
  docker network rm $networks
else
  echo "Nenhuma rede legada encontrada."
fi

echo "==> Volumes"
volumes=$(docker volume ls -q -f "label=com.docker.compose.project=${PROJECT}")
if [ -n "$volumes" ]; then
  docker volume rm $volumes
else
  echo "Nenhum volume legado encontrado."
fi

echo "==> docker ps"
docker ps --format 'table {{.Names}}\t{{.Label "com.docker.compose.project"}}\t{{.Ports}}'
