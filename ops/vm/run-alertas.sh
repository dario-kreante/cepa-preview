#!/usr/bin/env bash
# Lanza el job diario de alertas (COMP-2609-06) en la VM UTalca. Lo usa el crontab de segicepa.
# Corre el motor de plazos, las alertas de licencias y las de recetas con actor "sistema".
# Mismo entorno Oracle que run-api.sh: sin LD_LIBRARY_PATH y TNS_ADMIN el modo Thick falla.
set -euo pipefail

mkdir -p "$HOME/sige-cepa/logs"

# El log estructurado va a ALERTAS_JOB_LOG (ver .env); acá solo cae lo que muera antes de
# configurarlo. Solo redirigir cuando no hay terminal (cron): a mano imprime directo.
LOG="$HOME/sige-cepa/logs/alertas-cron.log"
if [ ! -t 1 ]; then
    exec >>"$LOG" 2>&1
fi

export LD_LIBRARY_PATH="$HOME/opt/instantclient_19_26${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}"
export TNS_ADMIN="$HOME/opt/tns"

cd "$HOME/sige-cepa/backend"

LOCK="$HOME/sige-cepa/logs/.alertas.lock"

# Guardia de proceso: que no se apilen dos ejecuciones. Si ya hay una corriendo, salir en
# silencio (un solo aviso). El job es idempotente, así que no se pierde nada.
exec {LOCKFD}>"$LOCK"
if ! flock -n "$LOCKFD"; then
    echo "run-alertas: el job de alertas ya está corriendo, se omite esta ejecución"
    exit 0
fi

exec timeout 30m .venv/bin/python -m app.scripts.alertas_job "$@"
