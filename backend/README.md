# Backend — Sistema CEPA

FastAPI + SQLAlchemy 2.0 + Alembic, portable entre PostgreSQL (dev/CI/contingencia) y
Oracle (producción objetivo). Ver `docs/superpowers/specs/2026-06-10-portabilidad-bd-postgres-fallback-design.md`.

## Requisitos
- `uv` (gestiona Python 3.12 y el entorno).
- PostgreSQL local (Homebrew): `brew services start postgresql@16`.

## Setup inicial
```bash
# Bases de datos locales (una sola vez)
psql postgres -c "CREATE ROLE cepa LOGIN PASSWORD 'cepa';"
createdb -O cepa cepa
createdb -O cepa cepa_test

cd backend
cp .env.example .env
uv sync
```

## Correr
```bash
uv run alembic upgrade head          # aplica el esquema
uv run uvicorn app.main:app --reload # http://127.0.0.1:8000  (/docs para Swagger)
```

## Tests
```bash
uv run pytest            # usa cepa_test (o TEST_DATABASE_URL)
```

## Migraciones
```bash
uv run alembic revision -m "descripcion"   # nueva migración (escribir portable)
uv run alembic upgrade head
uv run alembic downgrade -1
```

## Cambiar de motor
Ver `docs/superpowers/runbooks/2026-06-10-switch-db-engine.md`.
