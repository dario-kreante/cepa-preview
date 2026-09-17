#!/usr/bin/env bash
# Lanza un modo del sync SALUTEM en la VM UTalca. Lo usa el crontab de segicepa.
# Uso: run-salutem-sync.sh <caliente|tibia|fria|backfill|vincular|estado> [opciones]
# Mismo entorno Oracle que run-api.sh: sin LD_LIBRARY_PATH y TNS_ADMIN el modo Thick falla.
set -euo pipefail

if [ "$#" -lt 1 ]; then
    echo "Uso: run-salutem-sync.sh <caliente|tibia|fria|backfill|vincular|estado> [opciones]" >&2
    exit 2
fi

MODO="$1"

mkdir -p "$HOME/sige-cepa/logs"

# El log estructurado va a SALUTEM_SYNC_LOG (ver .env); acá solo cae lo que muera antes de
# configurarlo. Solo redirigir cuando no hay terminal (cron): así "estado" a mano imprime
# directo, y esto corre antes de cualquier otra cosa que pudiera fallar.
LOG="$HOME/sige-cepa/logs/salutem-sync-cron.log"
if [ ! -t 1 ]; then
    exec >>"$LOG" 2>&1
fi

export LD_LIBRARY_PATH="$HOME/opt/instantclient_19_26${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}"
export TNS_ADMIN="$HOME/opt/tns"

cd "$HOME/sige-cepa/backend"

LOCK="$HOME/sige-cepa/logs/.salutem-sync-$MODO.lock"

case "$MODO" in
    caliente) TIMEOUT=20m ;;
    tibia) TIMEOUT=55m ;;
    fria) TIMEOUT=3h ;;
    vincular) TIMEOUT=1h ;;
    estado) TIMEOUT=2m ;;
    backfill) TIMEOUT="" ;;
    *) TIMEOUT="" ;;
esac

if [ -n "$TIMEOUT" ]; then
    CMD=(timeout "$TIMEOUT" .venv/bin/python -m app.scripts.salutem_sync "$@")
else
    CMD=(.venv/bin/python -m app.scripts.salutem_sync "$@")
fi

# Guardia de proceso: que no se apilen dos ejecuciones del mismo modo. Si ya hay una
# corriendo, salir en silencio (un solo aviso) en vez de competir por el lease en BD.
exec {LOCKFD}>"$LOCK"
if ! flock -n "$LOCKFD"; then
    echo "run-salutem-sync: $MODO ya está corriendo, se omite esta ejecución"
    exit 0
fi

exec "${CMD[@]}"
