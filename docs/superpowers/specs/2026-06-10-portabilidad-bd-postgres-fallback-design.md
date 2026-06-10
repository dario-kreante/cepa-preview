# Diseño — Portabilidad de base de datos: Postgres como contingencia de Oracle

- **Fecha:** 2026-06-10
- **Estado:** Aprobado (diseño)
- **Contexto del proyecto:** Sistema CEPA (Universidad de Talca). Backend **FastAPI (Python)** (ver `docs/issues/00-decisiones-v4.md` D14).
- **Enfoque elegido:** A — Portable por defecto; Postgres como motor de trabajo, Oracle como target de producción.

## Problema

La habilitación de la instancia **Oracle** por parte de la Universidad está demorada y existe el
riesgo de que deba abortarse. Necesitamos que el sistema tenga la robustez para operar sobre
**PostgreSQL** —desplegable en los servidores de la U vía SSH— sin reescritura, en caso de que
Oracle se retrase más o se descarte definitivamente.

Restricción adicional: hoy **no existe** la instancia Oracle, por lo que ni siquiera es posible
desarrollar contra Oracle todavía. La contingencia (Postgres) y *lo único disponible ahora* son
el mismo motor.

## Principio rector

> Un fallback que nunca se ejecuta no es un fallback seguro.

La robustez **no** proviene de "tener Postgres por si acaso", sino de **ejercer Postgres de forma
continua en desarrollo y CI** mientras producción apunta a Oracle. Así, el día que (eventualmente)
haya que abortar Oracle, el camino Postgres ya está probado y en verde — no es un salto al vacío.

## Decisión de roles por motor

- **Oracle:** motor objetivo de **producción** (cuando la U lo habilite). Sigue siendo el primario
  de la estrategia.
- **PostgreSQL:** motor de **desarrollo, CI y contingencia de producción**. Es lo que se corre hoy.

## Arquitectura de la capa de datos

| Pieza | Elección | Rol |
|---|---|---|
| ORM | **SQLAlchemy 2.0** (modelos declarativos, tipado) | Abstrae el dialecto; el mismo modelo corre en Postgres y Oracle |
| Migraciones | **Alembic** | Una sola historia de migraciones, aplicable a ambos motores |
| Driver Postgres | **psycopg (v3)** | Desarrollo/CI y contingencia |
| Driver Oracle | **python-oracledb** | Producción objetivo |
| Config | **pydantic-settings** + `DATABASE_URL` por entorno | Cambiar de motor = cambiar una variable + correr migraciones |
| Sesión/engine | Módulo único (`app/db/session.py`) | Único lugar donde vive el detalle del motor |

**Invariante de diseño:** ningún módulo de negocio conoce el motor subyacente. Solo `session.py`
lee `DATABASE_URL`. Todo lo demás habla SQLAlchemy.

## Reglas de portabilidad (anti-lock-in)

Disciplina obligatoria en el código; es lo que mantiene el fallback real:

- **Tipos genéricos de SQLAlchemy** (`String`, `Numeric`, `DateTime(timezone=True)`, `Boolean`,
  `JSON`) — nunca `VARCHAR2`/`NUMBER`/`JSONB` directos. SQLAlchemy mapea al tipo nativo de cada motor.
- **Claves primarias con `Identity()`**, no `SERIAL` (PG) ni secuencias Oracle a mano. (El folio de
  CEPA-011 es lógica de negocio aparte; esta regla aplica a los PK subrogados.)
- **Sin SQL crudo con dialecto.** Si se requiere `text()`, que sea SQL portable; prohibido `ROWNUM`,
  `ON CONFLICT`, `MERGE` y `LIMIT/OFFSET` específicos — paginación vía ORM.
- **Identificadores en minúscula y ≤30 caracteres** (límite histórico de Oracle). Relevante para
  tablas como el log de auditoría.
- **Fechas siempre en UTC**, tipo `DateTime(timezone=True)`.
- **Upserts en capa de aplicación**, no en SQL específico del motor.

## CI dual-target

- **Job Postgres — siempre obligatorio.** Toda la suite corre contra un Postgres real
  (service container) en cada push. Lo no-portable se rompe aquí, de inmediato.
  **Un PR no mergea si este job está rojo.**
- **Job Oracle — gated.** Mientras no haya instancia, corre contra **Oracle XE / oracle-free** en
  contenedor, marcado *allowed-to-fail*. Cuando la U habilite Oracle real, pasa a **obligatorio**.
- **Tests contra DB real, nunca SQLite** (SQLite mentiría sobre la portabilidad). Se usa Postgres/
  Oracle real vía service container o testcontainers.

Matiz operativo: el contenedor Oracle XE/free arranca lento (~1–2 min) y es pesado; por eso es un
job separado y *gated*, que no frena el loop de desarrollo (rápido, solo Postgres).

## Migraciones

- Migraciones Alembic escritas de forma portable; deben aplicar limpiamente a **ambos** motores.
- Una sola historia de migraciones; el CI dual-target valida que corran en Postgres y Oracle.

## Despliegue de contingencia (servidor U vía SSH)

- **Producción objetivo:** Oracle (cuando exista).
- **Contingencia:** Postgres en el servidor de la U. Dos caminos documentados:
  - **Docker compose** (`api` + `postgres` + `nginx`) si el servidor tiene Docker — reproducible,
    aislado.
  - **Bare-metal** (respaldo): Postgres del SO + `systemd`, API con `gunicorn`/`uvicorn` detrás de
    `nginx`.
- **Switch Oracle→Postgres** = cambiar `DATABASE_URL` + driver + `alembic upgrade head`. Queda como
  **runbook escrito**, no improvisación.
- **Backups:** `pg_dump` (Postgres) / `expdp` (Oracle).

## Desarrollo local (macOS, sin Docker pesado)

- **Postgres nativo vía Homebrew** (`brew install postgresql@16`, corre como brew service) — huella
  mínima, sin Docker en el equipo.
- `.env` con `DATABASE_URL` local.
- **Oracle nunca se instala en local.** Solo aparece en CI (contenedor efímero) o en producción.

### Reparto de motores por entorno

| Entorno | Motor | ¿Oracle local? |
|---|---|---|
| Mac (desarrollo) | Postgres nativo (Homebrew) | No |
| CI — job principal | Postgres (service container) | No |
| CI — job de portabilidad | Oracle XE/free (contenedor, lo levanta CI) | No (lo gestiona CI) |
| Producción (futuro) | Oracle real de la U | Sí, en el servidor; no en el equipo |

## Impacto en las specs (a ejecutar tras aprobación)

1. **`docs/issues/README.md`** — línea de stack:
   `Oracle (producción objetivo) · PostgreSQL (desarrollo/CI y contingencia) vía SQLAlchemy + Alembic`.
2. **`docs/issues/00-decisiones-v4.md`** — nueva **D15: Estrategia de portabilidad de base de datos**
   (Oracle primario, Postgres contingencia ejercida en CI, reglas anti-lock-in, runbook de switch).
3. **`docs/issues/EPIC-00-plataforma-auth-rbac.md` / CEPA-003** — redacción agnóstica de motor donde
   hoy dice "(Oracle)": inmutabilidad del log verificada a nivel de aplicación y de base de datos
   (Oracle o Postgres); el "fuera de alcance: provisionamiento de Oracle" pasa a "provisionamiento
   del motor de base de datos".

## Fuera de alcance

- Implementación del backend FastAPI en sí (modelos, endpoints) — esto es solo la estrategia de
  portabilidad de datos.
- Selección final entre Docker vs. bare-metal en el servidor de la U (se confirma cuando se conozca
  el entorno; el diseño cubre ambos).
- Integración con SALUTEM/IMED (cubierta por EPIC-12).

## Criterios de éxito

- El backend corre íntegramente sobre Postgres en local y CI sin Oracle instalado.
- La suite de tests pasa contra Postgres en cada commit (job obligatorio).
- Cuando Oracle esté disponible, la misma suite pasa contra Oracle activando el job gated, sin
  cambios de código de negocio.
- Cambiar de motor en un despliegue se reduce a config + migraciones, documentado en un runbook.
