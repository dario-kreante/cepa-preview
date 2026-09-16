#!/usr/bin/env bash
# Lanza un modo del sync SALUTEM en la VM UTalca. Lo usa el crontab de segicepa.
# Uso: run-salutem-sync.sh <caliente|tibia|fria|backfill|vincular|estado> [opciones]
# Mismo entorno Oracle que run-api.sh: sin LD_LIBRARY_PATH y TNS_ADMIN el modo Thick falla.
set -euo pipefail

export LD_LIBRARY_PATH="$HOME/opt/instantclient_19_26${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}"
export TNS_ADMIN="$HOME/opt/tns"

mkdir -p "$HOME/sige-cepa/logs"
cd "$HOME/sige-cepa/backend"
# El log estructurado va a SALUTEM_SYNC_LOG (ver .env); acá solo cae lo que muera antes de configurarlo.
exec .venv/bin/python -m app.scripts.salutem_sync "$@" >> "$HOME/sige-cepa/logs/salutem-sync-cron.log" 2>&1
