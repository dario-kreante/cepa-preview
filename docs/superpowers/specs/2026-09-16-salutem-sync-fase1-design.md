# Diseño — Sincronización SALUTEM, fase 1 (lectura): carga inicial + sync cada 5 minutos

> **Estado:** aprobado por el usuario el 2026-09-16 ("todo SALUTEM, desde el primer día, cada 5 min").
> **Alcance:** solo lectura sobre SALUTEM. Respeta v4 D12 ("el aplicativo no escribe sobre SALUTEM").
> La escritura (fase 2) queda fuera y requiere reabrir D12 con Pilar y DTI.

## Contexto

Hoy la integración es un *pull* manual por folio (`POST /api/v1/fichas-clinicas/pull-salutem`): resuelve
el RUT, lista las atenciones de la persona y guarda en `ficha_clinica` las que caen en la ventana del
ingreso. Solo se entera de SALUTEM cuando alguien aprieta el botón.

Se quiere tener en el CEPA **toda** la información de SALUTEM (empresa 96, que es exclusiva del CEPA),
desde el primer día con datos, y mantenerla al día con un retraso máximo de ~5 minutos.

### Restricciones de la API (verificadas en QA el 2026-09-07 y en la doc v2.1 el 2026-09-16)

| Restricción | Consecuencia para el diseño |
|---|---|
| No hay webhooks ni filtro por fecha de modificación | Sync por *polling* + comparación de contenido (hash) |
| `/cita` acepta un solo día calendario y exige `citaEstadoId` | Cada día cuesta 9 llamadas (una por estado) |
| `/cita` filtra por `tipo` 1 = fecha de la cita, 2 = fecha de creación | La creación detecta citas nuevas; la fecha de cita detecta cambios de estado |
| `/atencion` con `persona_id` lista la historia completa de la persona | Sirve para verificar completitud de la carga inicial |
| `/atencion` con `persona_id` + `cita_id` trae el contenido clínico | Una llamada por atención |
| `/personas` por `persona_id` o por RUT | Una llamada por persona nueva |
| Sin paginación, HTTP siempre 200, errores en el cuerpo | Ya lo absorbe `SalutemHttpClient` |
| No se conoce el límite de llamadas | Ritmo configurable, por defecto 2 llamadas/s |
| No existe endpoint "primer día con datos" | La carga inicial lo descubre recorriendo hacia atrás |

## Decisiones

1. **Todo SALUTEM**, no solo pacientes con ingreso CEPA. La vinculación con ingresos es un paso posterior.
2. **Desde el primer día con datos**, descubierto automáticamente.
3. **Ventana caliente cada 5 minutos.**
4. **Copia local separada del dominio CEPA** (ver Arquitectura).
5. **Procesos fuera de uvicorn**, lanzados por el cron de `segicepa` en la VM. El watchdog reinicia la API
   y cortaría un sync a la mitad; además la API corre con recursos justos (2 vCPU, 1,9 GB).
6. **Nunca se borra nada** de la copia: lo que desaparece de SALUTEM se marca.

## Arquitectura

```
                      ┌──────────────── paso 1: copiar ────────────────┐   ┌──── paso 2: vincular ────┐
SALUTEM (solo GET) ──▶│ salutem_persona · salutem_cita · salutem_atencion│──▶│ ficha_clinica (por RUT + │
                      │ (contenido crudo + hash + marcas de tiempo)      │   │ ventana del ingreso)     │
                      └───────────────────────────────────────────────────┘   └──────────────────────────┘
                                  ▲ salutem_sync_dia (checkpoint)  ▲ salutem_sync_ejecucion (bitácora)
                                  └────────── salutem_sync_lease (un proceso a la vez) ─────────┘
```

- **Paso 1 (copiar)** solo habla con SALUTEM y solo escribe en las tablas `salutem_*`.
- **Paso 2 (vincular)** no habla con SALUTEM: lee la copia y actualiza el dominio CEPA. Se puede
  re-ejecutar entero sin costo de red (por ejemplo, si cambia la regla de ventana del ingreso).

Módulos nuevos:

```
backend/app/integrations/salutem/
  protocol.py            # + obtener_persona(salutem_id)
  client.py              # + implementación HTTP y stub de obtener_persona
backend/app/models/salutem_copia.py      # SalutemPersona, SalutemCita, SalutemAtencion
backend/app/models/salutem_sync.py       # SalutemSyncDia, SalutemSyncEjecucion, SalutemSyncLease
backend/app/services/salutem_sync/
  hash.py                # hash canónico del contenido
  ritmo.py               # limitador de llamadas + reintentos
  lease.py               # adquirir / renovar / liberar
  copia.py               # upsert con detección de cambios y marcas de desaparición
  barrido.py             # barrer un día (9 estados, tipo 1 o 2) y traer atenciones/personas nuevas
  backfill.py            # carga inicial reanudable
  incremental.py         # ventanas caliente / tibia / fría
  vinculacion.py         # paso 2: copia → ficha_clinica
backend/app/scripts/salutem_sync.py      # CLI: backfill | caliente | tibia | fria | vincular | estado
backend/app/routers/salutem_sync.py      # GET /api/v1/salutem/sync/estado (Coordinación)
backend/migrations/versions/1250_salutem_copia.py
```

El guard de D12 (`tests/test_salutem_no_escribe.py`) sigue vigente: todos los servicios nuevos usan
`SalutemClientProtocol`, que no tiene métodos de escritura, y los nombres evitan
create/update/delete/push/write/patch.

## Modelo de datos (nombres ≤ 30 caracteres, portables Oracle/Postgres)

**`salutem_persona`**
| Columna | Tipo | Nota |
|---|---|---|
| `salutem_id` | BigInteger PK | `SALUTEM_ID` |
| `rut` | String(12), índice, nullable | RUT normalizado CEPA (`<cuerpo><DV>`), para vincular |
| `contenido` | PortableJSON | respuesta cruda de `demograficos` |
| `hash_contenido` | String(64) | sha256 del contenido canónico (`hash` se evita por ser palabra clave en Oracle) |
| `visto_primera_vez` / `visto_ultima_vez` / `cambiado_en` | DateTime(tz) | |

**`salutem_cita`**
| Columna | Tipo | Nota |
|---|---|---|
| `cita_id` | BigInteger PK | |
| `persona_id` | BigInteger, índice | sin FK: la persona puede llegar después |
| `fecha_cita` | Date, índice | |
| `fecha_creacion` | DateTime, nullable | `citaFechaCreacion` |
| `estado_id` | Integer | |
| `contenido`, `hash_contenido`, `visto_*`, `cambiado_en` | | igual que persona |
| `desaparecida_en` | DateTime(tz), nullable | no volvió en un barrido completo de su día |

**`salutem_atencion`**
| Columna | Tipo | Nota |
|---|---|---|
| `cita_id` | BigInteger PK | una atención por cita |
| `persona_id` | BigInteger, índice | |
| `fecha_cita` | Date, índice | |
| `contenido`, `hash_contenido`, `visto_*`, `cambiado_en`, `desaparecida_en` | | |
| `hash_vinculado` | String(64), nullable | hash que el paso 2 ya aplicó; si difiere de `hash_contenido`, está pendiente |

**`salutem_sync_dia`** — checkpoint de la carga inicial
| `fecha` Date + `tipo` Integer (PK compuesta) | `completado_en` DateTime(tz) | `citas` Integer |

**`salutem_sync_ejecucion`** — bitácora
| `id` PK | `modo` String(20) | `inicio`, `fin` | `estado` (`en_curso`/`ok`/`con_errores`/`error`/`omitida`) |
| `llamadas`, `nuevos`, `cambiados`, `desaparecidos` Integer | `error` String(2000) nullable |

**`salutem_sync_lease`** — una fila por nombre (`"salutem"`)
| `nombre` String(30) PK | `dueno` String(80) | `vence_en` DateTime(tz) |

Cambio en tabla existente — **`ficha_clinica`**: se agregan `salutem_cita_id` (BigInteger, nullable,
índice **no único**: Oracle consideraría duplicadas dos filas `(ingreso_id, NULL)` de fichas push) y `eliminada_en_origen` (DateTime(tz), nullable). La migración rellena `salutem_cita_id` desde
`contenido.citaId` en las filas con `origen = 'SALUTEM'` (en Python, porque el JSON en Oracle es CLOB).

## Detección de cambios

- `hash = sha256(json.dumps(contenido, sort_keys=True, ensure_ascii=False, separators=(",", ":")))`.
- Upsert por id:
  - no existe → insertar, `nuevos += 1`;
  - existe con otro hash → reemplazar contenido, `cambiado_en = ahora`, `cambiados += 1`;
  - existe igual → solo `visto_ultima_vez = ahora`.
  - si tenía `desaparecida_en` y vuelve a aparecer → se limpia la marca (cuenta como cambio).
- **Riesgo a verificar en QA:** que SALUTEM no incluya campos volátiles (tokens, marcas de tiempo de la
  consulta) que cambien el hash sin cambio real. Si los hay, `hash.py` los excluye con una lista explícita.

## Barrido de un día

`barrer_dia(fecha, tipo)`:
1. Para cada uno de los 9 estados: `listar_citas(fecha, estado, tipo)`. Upsert de cada cita.
2. Si `tipo == FECHA_CITA` y **las 9 llamadas terminaron bien**: las citas guardadas con `fecha_cita = fecha`
   que no volvieron se marcan `desaparecida_en`. (Con fecha de creación no se marca nada: una cita puede
   cambiar de día.)
3. Para cada persona que no está en `salutem_persona`: `obtener_persona(persona_id)`.
4. Para cada cita en estado Atendido (3) que es nueva, cambió, o no tiene atención guardada:
   `obtener_atencion(persona_id, cita_id)`. `None` → si existía, `desaparecida_en`.
5. Todo el día se confirma en **una transacción** al final: si el proceso muere, el día se repite entero
   (es idempotente).

Hipótesis a confirmar en QA: una atención solo existe para citas en estado Atendido. Si aparecen
atenciones en otros estados (por ejemplo Recepcionado), se amplía la lista en configuración.

## Carga inicial (backfill)

`python -m app.scripts.salutem_sync backfill [--desde AAAA-MM-DD] [--hasta-futuro 180]`

1. **Futuro:** barre por fecha de cita desde mañana hasta +180 días (agendas ya creadas).
2. **Pasado:** desde hoy hacia atrás, día por día, por fecha de cita. Salta los días ya registrados en
   `salutem_sync_dia` (reanudable).
3. **Parada:** con `--desde`, se detiene en esa fecha. Sin `--desde`, se detiene tras **365 días seguidos
   sin citas** (configurable: `SALUTEM_BACKFILL_DIAS_VACIOS`) y registra el primer día con datos encontrado.
4. **Verificación de completitud:** para cada persona de la copia, `listar_atenciones(persona_id)` (una
   llamada por persona). Toda atención que no esté en la copia se trae; si su fecha es anterior al primer día
   barrido, el comando lo informa y sugiere re-ejecutar con `--desde` más antiguo.
5. Al terminar, ejecuta el paso 2 (vinculación) completo.

Estimación con el volumen visto en QA (~50 citas/día): 2 años ≈ 6.600 llamadas de citas + ~30.000 de
atenciones + personas; a 2 llamadas/s, 5–6 horas. Se lanza fuera de horario con `nohup`.

Mientras corre, tiene el lease: los sync incrementales del cron registran `omitida` y salen.

## Sync incremental

| Modo | Cron | Qué barre | Estimación de llamadas |
|---|---|---|---|
| `caliente` | `*/5 * * * *` | por creación: hoy (y ayer hasta 01:00); por fecha de cita: hoy y mañana | ~36 + atenciones nuevas |
| `tibia` | `7 * * * *` | por fecha de cita: últimos 7 días y próximos 30; re-trae atenciones de los últimos 7 días | ~330 + ~350 |
| `fria` | `30 3 * * *` | por fecha de cita: últimos 90 días y próximos 180; re-trae atenciones de los últimos 30 días; vinculación completa | ~2.500 + ~1.500 |

"Hoy" se calcula en `America/Santiago`. Cada modo termina ejecutando la vinculación de lo pendiente
(`hash_contenido != hash_vinculado`), salvo `fria`, que re-vincula todo.

## Paso 2: vinculación con el dominio CEPA

Para cada atención pendiente:
1. RUT de la persona (`salutem_persona.rut`) → `Paciente` por RUT. Sin paciente CEPA → queda pendiente
   (sin error); se reintenta en la siguiente vinculación.
2. Ingresos del paciente cuya ventana contiene `fecha_cita` (regla actual `_en_ventana_del_ingreso`).
3. Por ingreso: upsert de `ficha_clinica` por `(ingreso_id, salutem_cita_id)`:
   nueva → insertar; cambió → reemplazar `contenido`; desaparecida → `eliminada_en_origen = ahora`.
4. `hash_vinculado = hash`.

Consecuencias:
- Un ingreso creado hoy recibe sus atenciones antiguas en la siguiente vinculación (como mucho 5 min),
  porque las atenciones sin paciente quedan pendientes. Para acotar el costo, la vinculación de los modos
  caliente/tibia considera pendientes también las atenciones de personas cuyo paciente CEPA tenga un
  ingreso creado o editado desde la última ejecución.
- El botón actual "pull-salutem" se mantiene igual (lectura directa a SALUTEM por RUT), pero ahora
  guarda `salutem_cita_id` y deduplica por esa columna, así no choca con las fichas que crea el sync.
  Mismo contrato HTTP.
- Licencias sugeridas no cambia: ya lee `ficha_clinica` en cada consulta. Debe ignorar fichas con
  `eliminada_en_origen`.

## Robustez

- **Lease** (`salutem_sync_lease`): `UPDATE … SET dueno, vence_en WHERE nombre = 'salutem' AND vence_en < ahora`;
  si afecta 0 filas, otro proceso lo tiene → ejecución `omitida`. Duración 10 min, renovada tras cada día
  barrido. Un proceso muerto libera solo al vencer. Portable, sin transacciones largas en Oracle.
- **Ritmo:** limitador de `SALUTEM_SYNC_LLAMADAS_POR_SEG` (2 por defecto).
- **Errores:**
  - `SalutemUnavailableError` → 3 reintentos con espera 2/4/8 s; si persiste, se aborta la ejecución (`error`).
  - `SalutemAuthError` → aborta de inmediato (credencial mal configurada; no insistir).
  - `SalutemRequestError` en un día → se registra, ese día no se marca completo, se sigue con el siguiente.
- **Fail-closed:** si `get_salutem_client()` devuelve el stub (sin credenciales), el comando sale con
  código ≠ 0 y no toca la copia.
- **Memoria:** se procesa y confirma día a día; nunca se carga la copia completa.
- **Bandera:** `SALUTEM_SYNC_HABILITADO=false` por defecto; el comando no hace nada si está apagada.

## Operación en la VM

- Script `~/sige-cepa/run-salutem-sync.sh <modo>`: exporta `LD_LIBRARY_PATH` y `TNS_ADMIN`, entra a
  `~/sige-cepa/backend` y ejecuta `.venv/bin/python -m app.scripts.salutem_sync <modo>`, con salida a
  `~/sige-cepa/logs/salutem-sync.log` (rotación por tamaño desde Python: `RotatingFileHandler`, 5 × 10 MB).
- Entradas de crontab de `segicepa` según la tabla de modos.
- Carga inicial: `nohup ~/sige-cepa/run-salutem-sync.sh backfill &` fuera de horario, **con la clave de
  producción**. Las pruebas con QA se hacen con `--desde` acotado.

## Observabilidad

- `GET /api/v1/salutem/sync/estado` (rol Coordinación): última ejecución por modo (estado, inicio, fin, contadores),
  primer día con datos, totales de la copia, atenciones pendientes de vincular, y `atrasado: true` si la última
  `caliente` exitosa tiene más de 20 minutos.
- `python -m app.scripts.salutem_sync estado`: lo mismo por consola.
- `python -m app.scripts.salutem_sync vincular [--todo]`: re-ejecuta solo el paso 2, con lease y bitácora.
- Pantalla en el frontend: fuera de esta fase (se usa el endpoint).

## Pruebas

- **Unitarias/integración (pytest, Postgres y Oracle en CI):** un `SalutemFalso` en memoria que implementa
  `SalutemClientProtocol`, con datos por día/estado y contador de llamadas. Casos: inserción; idempotencia
  (segundo barrido sin cambios = 0 nuevos/0 cambiados); cambio de contenido; desaparición y reaparición;
  un estado que falla no marca desaparecidas; checkpoint y reanudación; parada por días vacíos; `--desde`;
  lease ocupado → `omitida`; lease vencido se recupera; auth error aborta; reintentos por indisponibilidad;
  vinculación (sin paciente → pendiente; con ingreso → ficha; cambio → contenido reemplazado; desaparecida →
  `eliminada_en_origen`); migración rellena `salutem_cita_id`; licencias sugeridas ignora eliminadas;
  guard D12.
- **Manual en QA:** backfill con `--desde` de una semana conocida (2025-01-22 tiene 52 citas); dos barridos
  seguidos del mismo día dan 0 cambios (valida estabilidad del hash); comparar conteos contra SALUTEM.

## Fuera de alcance

- Escribir en SALUTEM (fase 2, requiere reabrir D12).
- Alimentar agendamiento (CEPA-061) con las citas de la copia: siguiente paso natural, spec aparte.
- Exámenes, archivos, prestaciones y reportería de SALUTEM.
- Pantalla de estado del sync en el frontend.

## Pendientes externos

- **Clave de producción** de SALUTEM (FabricApp). Sin ella la carga inicial solo puede validarse en QA.
- **Límite de llamadas** de la API (FabricApp): ajustar `SALUTEM_SYNC_LLAMADAS_POR_SEG`.
- **Aviso a DTI (Mario):** se guardará la historia clínica completa de SALUTEM en el Oracle de la UTalca.
  No bloquea implementar; sí correr la carga inicial en producción.
