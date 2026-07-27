# Runbook — Deploy de staging del backend CEPA en PaaS de contenedores

El backend es un servidor de larga duración (FastAPI/uvicorn) con Postgres. Encaja en un
PaaS de contenedores (Render / Railway / Fly.io), **no** en Vercel (serverless). El
contenedor ya está preparado: `backend/entrypoint.sh` aplica migraciones, siembra el admin
(si hay credenciales) y arranca uvicorn en `$PORT`. `app.config` normaliza el
`DATABASE_URL` que entregan los PaaS (`postgres://`/`postgresql://` → `postgresql+psycopg://`).

## Variables de entorno (todas las plataformas)

| Variable | Obligatoria | Notas |
|----------|-------------|-------|
| `DATABASE_URL` | Sí | Cadena de conexión de la Postgres (externa o gestionada por el PaaS). Se normaliza sola y conserva parámetros como `sslmode=require`. |
| `JWT_SECRET` | Sí | Secreto fuerte. En Render se autogenera; en otros, generar uno. |
| `SEED_ADMIN_USERNAME` | Recomendada | Crea el usuario inicial de Coordinación al arrancar (idempotente). |
| `SEED_ADMIN_PASSWORD` | Recomendada | Junto con la anterior. Cambiar tras el primer login. |
| `SEED_ADMIN_NOMBRE` | No | Default "Coordinación". |
| `RATE_LIMIT_PER_MINUTE`, `LOGIN_MAX_INTENTOS`, etc. | No | Tienen defaults razonables (D13). |
| `SMTP_*` | No | Vacío = correo de alertas desactivado (la alerta in-app sigue). |

> **Datos sensibles (dominio clínico):** staging NO debe cargar datos reales de pacientes.
> El arranque solo crea el usuario admin; no hay seed de pacientes.

## Opción A — Render + Postgres externa (recomendada, declarativa)

Hay un `render.yaml` (Blueprint) en la raíz del repo. La BD **no** la gestiona el blueprint:
ver "La Postgres free de Render caduca" más abajo.

1. Crear una Postgres gratuita sin expiración (Neon o Supabase) y copiar su cadena de conexión.
   En Neon: usar la conexión **directa** (no la `-pooler`), porque Alembic corre DDL al arrancar.
2. En Render: **New → Blueprint** y conectar este repositorio (rama a desplegar). Render crea el
   web service Docker `cepa-backend-staging` y genera `JWT_SECRET`.
3. En el servicio → **Environment**, definir `DATABASE_URL` (paso 1), `SEED_ADMIN_USERNAME` y
   `SEED_ADMIN_PASSWORD`.
4. Deploy. El healthcheck es `GET /health`. Swagger en `/docs`.
5. Verificar: `curl https://<servicio>.onrender.com/health` → `{"status":"ok"}`; login con el
   admin sembrado en `POST /api/v1/auth/login`.

### La Postgres free de Render caduca (incidente 2026-07)

La Postgres `free` expira a los ~30 días y Render borra los datos poco después. Al expirar, el
servicio entero deja de responder: el entrypoint corre `alembic upgrade head` con `set -e`, así
que sin BD el contenedor muere antes de escuchar `$PORT` y el edge de Render deja las peticiones
**colgadas sin respuesta** (no devuelve 5xx). Síntoma en el frontend: pantalla de carga eterna.

Diagnóstico rápido cuando staging "no carga":

```bash
curl -s -o /dev/null -w "%{http_code} %{time_total}s\n" --max-time 90 https://cepa-backend-staging.onrender.com/health
```

`200` en ~50s = solo era el cold start del plan free. Sin respuesta a los 90s = el servicio no
levanta; revisar Events/Logs del servicio y el estado de la BD.

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
- Para resetear staging: vaciar/recrear la BD y redeploy (el entrypoint reconstruye el esquema
  y vuelve a sembrar el usuario de Coordinación).
- Portabilidad Oracle⇄Postgres validada en CI (job gated verde).
- El frontend en `frontend/` sí consume este backend (`VITE_API_BASE_URL`, horneada en build →
  cambiarla exige redeploy en Vercel). Su cliente HTTP corta a los 60s y muestra un error
  explícito si el backend no responde, en vez de quedarse cargando.
