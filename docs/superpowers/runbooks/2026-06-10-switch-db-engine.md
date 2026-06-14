# Runbook — Cambiar el motor de base de datos (Oracle ⇄ PostgreSQL)

Aplica la estrategia de D15. El motor se selecciona por `DATABASE_URL`; no hay cambios de código.

## Formato de DATABASE_URL
- PostgreSQL: `postgresql+psycopg://USUARIO:CLAVE@HOST:5432/BASE`
- Oracle:     `oracle+oracledb://USUARIO:CLAVE@HOST:1521/?service_name=PDB`

## Procedimiento de switch
1. Provisionar el motor destino y crear la base/esquema vacío.
2. Definir `DATABASE_URL` apuntando al motor destino (env del servicio o `.env`).
3. Aplicar el esquema: `uv run alembic upgrade head`.
4. (Si hay datos) migrar datos con la herramienta del motor destino — ver Backups.
5. Reiniciar la API. Verificar `GET /health` y un `GET /api/v1/audit-log`.

## Despliegue de contingencia (Postgres en servidor U vía SSH)
- **Con Docker:** `docker compose up -d --build` (levanta db + api; la api corre
  `alembic upgrade head` al arrancar).
- **Bare-metal (sin Docker):**
  1. Instalar Postgres del SO y crear rol/base.
  2. `uv sync --no-dev` en el host.
  3. `DATABASE_URL=... uv run alembic upgrade head`.
  4. Servir con `uv run uvicorn app.main:app --host 0.0.0.0 --port 8000` (o gunicorn
     con workers uvicorn) detrás de `nginx` con TLS.

## Backups
- PostgreSQL: `pg_dump` / `pg_restore`.
- Oracle: `expdp` / `impdp`.

## Reglas que mantienen el switch barato (no romper)
- Solo tipos genéricos de SQLAlchemy; nada de SQL específico de motor.
- PK por `Identity()`; identificadores en minúscula y ≤30 chars; fechas en UTC.
- Toda migración debe pasar el job Oracle gated en CI antes de considerarse portable.
