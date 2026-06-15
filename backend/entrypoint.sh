#!/bin/sh
# Entrypoint para despliegue en PaaS de contenedores (Render / Railway / Fly.io).
# - Aplica las migraciones Alembic (idempotente).
# - Crea el usuario inicial de Coordinación si se proveen SEED_ADMIN_* (idempotente).
# - Arranca uvicorn en el puerto que inyecta la plataforma ($PORT) o 8000 por defecto.
set -e

echo "[entrypoint] Aplicando migraciones (alembic upgrade head)..."
alembic upgrade head

if [ -n "$SEED_ADMIN_USERNAME" ] && [ -n "$SEED_ADMIN_PASSWORD" ]; then
  echo "[entrypoint] Sembrando usuario de Coordinación '$SEED_ADMIN_USERNAME' (idempotente)..."
  python -m app.scripts.seed_admin \
    --username "$SEED_ADMIN_USERNAME" \
    --password "$SEED_ADMIN_PASSWORD" \
    --nombre "${SEED_ADMIN_NOMBRE:-Coordinación}"
fi

PORT="${PORT:-8000}"
echo "[entrypoint] Iniciando uvicorn en 0.0.0.0:$PORT ..."
exec uvicorn app.main:app --host 0.0.0.0 --port "$PORT"
