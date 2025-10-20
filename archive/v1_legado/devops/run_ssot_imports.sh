#!/usr/bin/env bash
set -euo pipefail

# ========================================
# SSOT Imports Runner
# ========================================
# Executa imports com cross-check automático
# Logs em logs/ssot_run_<timestamp>.log

cd /app
TS=$(date +%Y%m%d_%H%M%S)
LOG="logs/ssot_run_${TS}.log"
CAT="ingestao/gsheets_catalog.json"

echo "[RUN] SSOT imports @ ${TS}" | tee -a "$LOG"
echo "Log: $LOG" | tee -a "$LOG"

# Função utilitária para escolher um par (sheet_id,gid) por heurística de nome do arquivo
pick_entry() {
  local hint="$1"
  python - <<PY
import json,sys,re
try:
    cat=json.load(open("$CAT",encoding="utf-8"))
except FileNotFoundError:
    print("", "")
    sys.exit(0)

hint=sys.argv[1].lower()

def score(e):
    f=e.get("file","").lower()
    s=e.get("sheet_id",""); g=e.get("gid","")
    # heurística leve por nome
    pts=0
    if any(k in f for k in [hint]): pts+=2
    if 'usuario' in f or 'users' in f: pts+= (hint=='usuarios')
    if 'evento' in f or 'agenda' in f or 'solicit' in f: pts+= (hint=='eventos')
    if 'disp' in f or 'dispon' in f: pts+= (hint=='disp')
    return pts

cands=sorted(cat.get("entries",[]), key=score, reverse=True)
if cands:
    e=cands[0]
    print(e["sheet_id"], e["gid"])
else:
    print("", "")
PY
}

# Usuarios
echo "[INFO] Buscando configuração para usuários..." | tee -a "$LOG"
read -r USERS_SID USERS_GID < <(pick_entry "usuarios")
echo "  Sheet ID: $USERS_SID, GID: $USERS_GID" | tee -a "$LOG"

# Eventos
echo "[INFO] Buscando configuração para eventos..." | tee -a "$LOG"
read -r EVTS_SID EVTS_GID < <(pick_entry "eventos")
echo "  Sheet ID: $EVTS_SID, GID: $EVTS_GID" | tee -a "$LOG"

# Disponibilidades
echo "[INFO] Buscando configuração para disponibilidades..." | tee -a "$LOG"
read -r DISP_SID DISP_GID < <(pick_entry "disp")
echo "  Sheet ID: $DISP_SID, GID: $DISP_GID" | tee -a "$LOG"

# Paths locais (se quiser manter cópias CSV locais também)
mkdir -p data/ingest || true
USERS_CSV=${USERS_CSV:-data/ingest/usuarios.csv}
EVENTS_CSV=${EVENTS_CSV:-data/ingest/eventos.csv}
DISP_CSV=${DISP_CSV:-data/ingest/disponibilidades.csv}

echo "[INFO] Paths CSV:" | tee -a "$LOG"
echo "  Usuários: $USERS_CSV" | tee -a "$LOG"
echo "  Eventos: $EVENTS_CSV" | tee -a "$LOG"
echo "  Disponibilidades: $DISP_CSV" | tee -a "$LOG"

# Verificar se arquivos CSV existem
for csv in "$USERS_CSV" "$EVENTS_CSV" "$DISP_CSV"; do
    if [ ! -f "$csv" ]; then
        echo "[WARN] CSV não encontrado: $csv" | tee -a "$LOG"
        echo "  Criando arquivo vazio..." | tee -a "$LOG"
        echo "email,nome" > "$csv"
    fi
done

# Executa os três importadores com cross-check (se tiver SID/GID)
echo "[INFO] Iniciando imports..." | tee -a "$LOG"

# Import Usuários
echo "[RUN] Importando usuários..." | tee -a "$LOG"
if [ -n "$USERS_SID" ] && [ -n "$USERS_GID" ]; then
    python manage.py import_usuarios "$USERS_CSV" \
        --sheet-id="$USERS_SID" \
        --gid="$USERS_GID" \
        --fonte="SSOT_CRON" 2>&1 | tee -a "$LOG"
else
    echo "[WARN] Sem configuração de Sheets para usuários, importando apenas CSV local" | tee -a "$LOG"
    python manage.py import_usuarios "$USERS_CSV" \
        --fonte="SSOT_CRON" 2>&1 | tee -a "$LOG"
fi

# Import Eventos
echo "[RUN] Importando eventos..." | tee -a "$LOG"
if [ -n "$EVTS_SID" ] && [ -n "$EVTS_GID" ]; then
    python manage.py import_eventos_abas "$EVENTS_CSV" \
        --sheet-id="$EVTS_SID" \
        --gid="$EVTS_GID" \
        --cutoff=2025-09-25 \
        --fonte="SSOT_CRON" 2>&1 | tee -a "$LOG"
else
    echo "[WARN] Sem configuração de Sheets para eventos, importando apenas CSV local" | tee -a "$LOG"
    python manage.py import_eventos_abas "$EVENTS_CSV" \
        --cutoff=2025-09-25 \
        --fonte="SSOT_CRON" 2>&1 | tee -a "$LOG"
fi

# Import Disponibilidades
echo "[RUN] Importando disponibilidades..." | tee -a "$LOG"
if [ -n "$DISP_SID" ] && [ -n "$DISP_GID" ]; then
    python manage.py import_disponibilidades "$DISP_CSV" \
        --sheet-id="$DISP_SID" \
        --gid="$DISP_GID" \
        --fonte="SSOT_CRON" 2>&1 | tee -a "$LOG"
else
    echo "[WARN] Sem configuração de Sheets para disponibilidades, importando apenas CSV local" | tee -a "$LOG"
    python manage.py import_disponibilidades "$DISP_CSV" \
        --fonte="SSOT_CRON" 2>&1 | tee -a "$LOG"
fi

echo "[OK] SSOT run finalizado -> $LOG" | tee -a "$LOG"

# Listar relatórios de cross-check gerados
echo "[INFO] Relatórios de cross-check:" | tee -a "$LOG"
for report in /app/docs/GSHEETS_CROSSCHECK_*.json; do
    if [ -f "$report" ]; then
        echo "  ✓ $report" | tee -a "$LOG"
    fi
done

echo "[DONE] SSOT imports concluídos com sucesso!" | tee -a "$LOG"
