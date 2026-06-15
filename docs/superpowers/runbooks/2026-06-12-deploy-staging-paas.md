# Runbook — Deploy de staging del backend CEPA en PaaS de contenedores

El backend es un servidor de larga duración (FastAPI/uvicorn) con Postgres. Encaja en un
PaaS de contenedores (Render / Railway / Fly.io), **no** en Vercel (serverless). El
contenedor ya está preparado: `backend/entrypoint.sh` aplica migraciones, siembra el admin
(si hay credenciales) y arranca uvicorn en `$PORT`. `app.config` normaliza el
`DATABASE_URL` que entregan los PaaS (`postgres://`/`postgresql://` → `postgresql+psycopg://`).

## Variables de entorno (todas las plataformas)

| Variable | Obligatoria | Notas |
|----------|-------------|-------|
| `DATABASE_URL` | Sí | La inyecta la BD gestionada del PaaS. Se normaliza sola. |
| `JWT_SECRET` | Sí | Secreto fuerte. En Render se autogenera; en otros, generar uno. |
| `SEED_ADMIN_USERNAME` | Recomendada | Crea el usuario inicial de Coordinación al arrancar (idempotente). |
| `SEED_ADMIN_PASSWORD` | Recomendada | Junto con la anterior. Cambiar tras el primer login. |
| `SEED_ADMIN_NOMBRE` | No | Default "Coordinación". |
| `RATE_LIMIT_PER_MINUTE`, `LOGIN_MAX_INTENTOS`, etc. | No | Tienen defaults razonables (D13). |
| `SMTP_*` | No | Vacío = correo de alertas desactivado (la alerta in-app sigue). |

> **Datos sensibles (dominio clínico):** staging NO debe cargar datos reales de pacientes.
> El arranque solo crea el usuario admin; no hay seed de pacientes.

## Opción A — Render (recomendada, declarativa)

Hay un `render.yaml` (Blueprint) en la raíz del repo.

1. En Render: **New → Blueprint** y conectar este repositorio (rama a desplegar).
2. Render crea la Postgres `cepa-staging-db` y el web service Docker `cepa-backend-staging`,
   e inyecta `DATABASE_URL` y un `JWT_SECRET` generado.
3. En el servicio → **Environment**, definir `SEED_ADMIN_USERNAME` y `SEED_ADMIN_PASSWORD`.
4. Deploy. El healthcheck es `GET /health`. Swagger en `/docs`.
5. Verificar: `curl https://<servicio>.onrender.com/health` → `{"status":"ok"}`; login con el
   admin sembrado en `POST /api/v1/auth/login`.

## Opción B — Railway

1. **New Project → Deploy from GitHub repo**; root del servicio = `backend/` (usa el Dockerfile).
2. **Add → Database → PostgreSQL**. Railway expone `DATABASE_URL` (referenciarla en el servicio).
3. Variables: `JWT_SECRET`, `SEED_ADMIN_USERNAME`, `SEED_ADMIN_PASSWORD`.
4. Railway inyecta `$PORT`; el entrypoint lo respeta. Deploy y verificar `/health`.

## Opción C — Fly.io

1. `fly launch --no-deploy` desde `backend/` (genera `fly.toml`; usa el Dockerfile). Ajustar
   `internal_port = 8000` y un `[http_service]` con health check a `/health`.
2. `fly postgres create` y `fly postgres attach` (setea `DATABASE_URL`).
3. `fly secrets set JWT_SECRET=... SEED_ADMIN_USERNAME=... SEED_ADMIN_PASSWORD=...`.
4. `fly deploy`. Verificar `/health`.

## Notas

- Las migraciones corren en cada arranque (`alembic upgrade head`), idempotentes.
- Para resetear staging: recrear la BD del PaaS y redeploy (el entrypoint reconstruye el esquema).
- Portabilidad Oracle⇄Postgres validada en CI (job gated verde); el PaaS usa Postgres gestionado.
- El frontend actual es un prototipo estático con datos mock (no consume este backend); su
  publicación (Vercel/GitHub Pages) es independiente.
