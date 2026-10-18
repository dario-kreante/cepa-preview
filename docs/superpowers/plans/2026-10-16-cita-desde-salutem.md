# Fase 2 — `cita` desde SALUTEM y alertas de citas — Plan de implementación

> **Para agentes:** SUB-SKILL REQUERIDA: usar superpowers:subagent-driven-development (recomendado) o superpowers:executing-plans para implementar este plan tarea por tarea. Los pasos usan checkboxes (`- [ ]`).

**Objetivo:** llenar la tabla `cita` con las citas reales de SALUTEM de los pacientes del CEPA, adaptar a esa fuente los 5 reportes que la leen, corregir la alerta "control médico" y agregar la alerta de inasistencia.

**Arquitectura:** el sync ya copia todas las citas de SALUTEM en `salutem_cita`. Un paso nuevo del orquestador (`citas_cepa.sincronizar_citas`) cruza esas citas con pacientes e ingresos del CEPA mediante SQL y hace un upsert en `cita` por `salutem_cita_id`. Ese mismo paso crea y resuelve alertas. Los reportes cuentan solo `origen='SALUTEM'` y las especialidades configuradas. La alerta "control médico" reutiliza `pacientes_con_hora_vigente` de la Fase 1.

**Stack:** FastAPI + SQLAlchemy 2 (Postgres y Oracle 19c), Alembic, pytest; React + vitest.

**Spec:** `docs/superpowers/specs/2026-10-16-cita-desde-salutem-design.md`, aprobada con los valores por defecto.

## Base de la rama

Crear `claude/cita-desde-salutem` desde `origin/claude/agenda-lista-trabajo` (el PR #53, Fase 1). Si #53 ya está mergeado, crearla desde `origin/main`. El PR se abre contra la misma base.

## Restricciones globales

- SQL portable a Postgres y Oracle 19c (D15): nada de `DISTINCT ON` ni funciones propias de un motor; booleanos con `true()`/`false()` y `TRIM` con `func.trim` de Core. Las listas `IN` van en lotes de 500 con el helper `_lotes` de `app/agendamiento/salutem.py` (hacerlo público como `lotes` en la Tarea 2 y actualizar sus usos).
- Solo lectura sobre SALUTEM (v4 D12).
- Migración nueva `1360`, con `down_revision = "1350"`.
- Actor de auditoría del sync: `sistema:salutem-sync`. Toda escritura del sync sobre `cita` o `alerta_notif` llama a `record_audit`.
- Configuración nueva en `app/config.py`, con el mismo patrón que `salutem_borradores_desde`:
  - `citas_salutem_desde: str = "2026-01-01"`, con la propiedad `citas_salutem_desde_fecha -> date` que lanza `ValueError` si el formato es inválido.
  - `citas_especialidades_reportes: str = ""`, con la propiedad `citas_especialidades_reportes_set -> frozenset[str]` en casefold; vacía significa "todas".
  - Ambas se documentan en `backend/.env.example`.
- La correspondencia de estados es exactamente la de la decisión 2 de la spec. RECEPCIONADO equivale a `agendada`.
- `DIAS_NOVEDAD_INASISTENCIA = 14`.
- Todo el texto visible va en español.
- Tests de backend: `cd backend && TEST_DATABASE_URL=postgresql+psycopg://cepa:cepa@localhost:5432/cepa_test_fase2 uv run pytest`. Hay que usar una BD propia, creada con `createdb -h localhost -U cepa cepa_test_fase2`, porque `cepa_test` la comparten varias sesiones. Al terminar el plan, borrarla con `dropdb`.
- Push con la cuenta gh `dario-kreante`.

## Foco de revisión

1. Una persona de SALUTEM que cruza con dos pacientes del SIGE (RUT duplicado): la cita se omite con un aviso y no se asigna a ninguno. → Test en la Tarea 2.
2. Una cita reprogramada a una fecha fuera de la ventana de su ingreso: la fila de `cita` se elimina. → Test en la Tarea 2.
3. Una corrida incremental en la que el paciente recibió hoy un ingreso nuevo: entran sus citas antiguas aunque esas `salutem_cita` no hayan cambiado. → Test en la Tarea 2.
4. Las filas de `cita` con `origen='SIGE'` (las del seed antiguo y las de las confirmaciones de prueba) no cuentan en ninguno de los 5 reportes. → Un test por reporte en la Tarea 4.
5. Un folio que solo tiene citas anuladas o futuras: adherencia devuelve `pct_adherencia = None` y no `0` ni un error. → Test en la Tarea 4.

---

### Tarea 1: Migración 1360, modelo y configuración

**Archivos:**
- Crear: `backend/migrations/versions/1360_cita_salutem.py`
- Modificar: `backend/app/models/cita.py`, `backend/app/config.py`, `backend/.env.example` y `backend/app/domain/enums_alertas.py`
- Test: `backend/tests/test_cita_salutem_modelo.py`

**Interfaces:**
- Produce:
  - Las columnas nuevas de `Cita` según la decisión 1 de la spec:
    - `salutem_cita_id: Mapped[int | None]` (BigInteger, `unique=True`)
    - `origen: Mapped[str]` (String(10), `default="SIGE"`, `server_default="SIGE"`)
    - `especialidad: Mapped[str | None]` (String(80))
    - `profesional_nombre: Mapped[str | None]` (String(160))
    - `profesional_id: Mapped[int | None]` (BigInteger, FK a `profesional.id`)
  - `TipoAlerta.INASISTENCIA = "inasistencia"`
  - La configuración descrita en las restricciones globales.
- La migración agrega las 5 columnas. Al ser `origen` `server_default 'SIGE'`, las filas existentes quedan en `SIGE`. Crea el índice único `uq_cita_salutem_cita_id` y la FK `fk_cita_profesional`, y siembra `config_alerta` con `tipo='inasistencia'`, `dias=0`, `habiles=False`, `activo=True`, `actualizado_por='migracion'` y `updated_at=now`, siguiendo el patrón de la `1300`. El downgrade borra esa fila de `config_alerta` y las alertas `inasistencia`, y quita las columnas.

- [ ] **Paso 1: Escribir los tests que fallan**
  - `test_cita_nueva_tiene_origen_sige_por_defecto`
  - `test_salutem_cita_id_unico`: dos filas con el mismo `salutem_cita_id` → `IntegrityError`; dos con `None` → se aceptan.
  - `test_config_alerta_inasistencia_sembrada`: existe la fila, con `activo=True`.
  - `test_citas_salutem_desde_fecha_por_defecto_y_invalida`: `Settings(citas_salutem_desde="2026-01-01").citas_salutem_desde_fecha == date(2026,1,1)`; `"x"` → `ValueError`.
  - `test_especialidades_reportes_set`: `" Médico/a , Psicología "` → `{"médico/a","psicología"}`; `""` → vacío.

- [ ] **Paso 2: Correr y confirmar que fallan**
  Comando: `uv run pytest tests/test_cita_salutem_modelo.py -v`

- [ ] **Paso 3: Implementar.**

- [ ] **Paso 4: Correr y confirmar que pasan, más la migración de ida y vuelta**
  Comando: `DATABASE_URL=…/cepa_test_fase2 uv run alembic downgrade 1350 && … upgrade head`
  Esperado: sin errores.

- [ ] **Paso 5: Commit**
  `git commit -m "feat(citas): columnas de origen SALUTEM en cita, configuración y tipo de alerta inasistencia"`

### Tarea 2: Importar citas de SALUTEM (`citas_cepa`)

**Archivos:**
- Crear: `backend/app/services/salutem_sync/citas_cepa.py`
- Modificar: `backend/app/agendamiento/salutem.py` (`_lotes` → `lotes`) y los módulos que lo importan
- Test: `backend/tests/salutem_sync/test_citas_cepa.py`

**Interfaces:**
- Consume: `filtro.cruce_con_paciente()`, `ficha_clinica._en_ventana_del_ingreso(fecha, ingreso)`, `profesional.SIN_PROFESIONAL_SALUTEM` y la configuración de la Tarea 1.
- Produce:
  - `estado_cita(estado_id: int | None) -> str | None`: función pura. Devuelve `None` si el estado es desconocido o nulo.
  - `@dataclass ResultadoCitas(creadas=0, actualizadas=0, eliminadas=0, estado_desconocido=0, sin_ingreso=0, ambiguas=0, agendadas_antiguas=0, alertas_inasistencia=0, alertas_resueltas=0, errores: list[str])`, con `sumar(otro)`.
  - `sincronizar_citas(db: Session, *, desde: datetime | None, ahora: datetime) -> ResultadoCitas`. No hace commit al final; hace commit por lote, como `vincular`.
  - `hoy` se calcula como `hoy_en_santiago(ahora)`.

**Algoritmo** (la parte que la firma no determina):
1. Candidatas:
   - `salutem_cita` con `fecha_cita >= citas_salutem_desde_fecha`, unida a `SalutemPersona` y a `Paciente` mediante `cruce_con_paciente()` (consulta SQL).
   - Si `desde` no es `None`, se toman además dos grupos: las que tienen `cambiado_en >= desde`, y todas las citas de los pacientes con algún `Ingreso.updated_at >= desde`.
   - Hay que incluir las desaparecidas, porque se usan para borrar.
   - Resultado: pares (`cita_id`, `paciente_id`).
2. Agrupar por `cita_id`. Si una cita trae más de un `paciente_id`, sumar 1 a `ambiguas`, registrar un aviso y saltarla.
3. Cargar en lote los ingresos de los pacientes y las `Cita` existentes por `salutem_cita_id`.
4. Por cita, cada una en su propio `db.begin_nested()`:
   - Si `desaparecida_en` está informado, o si no hay fecha, o si la fecha no cae en la ventana de ningún ingreso: eliminar la `Cita` existente (`DELETE` auditado; suma a `eliminadas`). Si no existía y la causa fue que no hay ingreso, sumar a `sin_ingreso`.
   - Si el estado es desconocido: sumar a `estado_desconocido` y no tocar nada.
   - En otro caso, el ingreso es el de `fecha_ingreso` más reciente cuya ventana contiene la fecha. `especialidad` y `profesional_nombre` salen de `contenido` (`especialidadNombre`, `profesionalNombre`): se recortan, y si quedan vacíos o son `SIN_PROFESIONAL_SALUTEM`, quedan en `None`.
   - `profesional_id` es el `Profesional.id` con `nombre == profesional_nombre`, cargado en lote.
   - Upsert con `origen='SALUTEM'`: suma a `creadas` o a `actualizadas`, y solo se audita si algo cambió.
5. Al final, contar `agendadas_antiguas`: filas de `cita` con `origen='SALUTEM'`, `estado='agendada'` y `fecha < hoy - 90 días`.
6. Las alertas no van en esta tarea, sino en la Tarea 3.

- [ ] **Paso 1: Escribir los tests que fallan.** Usar helpers propios para `Paciente`, `Ingreso`, `SalutemPersona` y `SalutemCita`, con `contenido` que incluya `especialidadNombre` y `profesionalNombre`.
  - `test_estado_cita_mapea_los_9_estados_y_desconocidos` (parametrizado: 1, 4, 5, 6, 7 y 8 → `agendada`; 3 → `realizada`; 9 → `inasistencia`; 2 → `anulada`; 99 y `None` → `None`).
  - `test_importa_cita_cruzando_por_rut` y `test_importa_cita_cruzando_por_persona_id`.
  - `test_ignora_personas_que_no_son_pacientes` (no hay fila y ningún contador sube).
  - `test_cita_fuera_de_ventana_no_se_importa_y_cuenta_sin_ingreso`.
  - `test_dos_ingresos_gana_el_mas_reciente`.
  - `test_cambio_de_estado_actualiza_la_fila`.
  - `test_cita_desaparecida_borra_la_fila`.
  - `test_reprogramada_fuera_de_ventana_borra_la_fila` (Foco 2).
  - `test_ingreso_nuevo_trae_citas_pasadas_en_corrida_incremental` (Foco 3): `desde` es posterior al `cambiado_en` de la cita, y el `updated_at` del ingreso es posterior a `desde`.
  - `test_persona_que_cruza_con_dos_pacientes_se_omite` (Foco 1).
  - `test_anterior_a_citas_salutem_desde_no_se_importa`.
  - `test_idempotente` (dos corridas → una sola fila; la segunda corrida no suma a `actualizadas`).
  - `test_resuelve_profesional_por_nombre_con_espacios`: `profesionalNombre="  Dra. Ana Rojas "`, y el catálogo tiene "Dra. Ana Rojas" → `profesional_id` enlazado.
  - `test_sin_profesional_queda_nulo`.
  - `test_cuenta_agendadas_antiguas`.
  - `test_estado_desconocido_no_toca_la_fila`.

- [ ] **Paso 2: Correr y confirmar que fallan.**

- [ ] **Paso 3: Implementar.**

- [ ] **Paso 4: Correr `tests/salutem_sync` completo y confirmar que pasa.**

- [ ] **Paso 5: Commit**
  `git commit -m "feat(citas): importar a cita las citas SALUTEM de los pacientes del CEPA"`

### Tarea 3: Alertas de citas (control médico corregida + inasistencia)

**Archivos:**
- Crear: `backend/app/services/alertas_citas.py`
- Modificar: `backend/app/services/alertas.py` (`_construir_hitos_control_medico` y `ejecutar_job_alertas`) y `backend/app/services/salutem_sync/citas_cepa.py` (llamar a las alertas)
- Test: `backend/tests/test_alertas_citas.py`

**Interfaces:**
- Consume: `agendamiento.salutem.pacientes_con_hora_vigente(db, paciente_ids, hoy)`, `ResultadoCitas` (Tarea 2) y `config_alertas.cargar_ventanas(db)`.
- Produce:
  - `alertas_citas.CASO_TIPO_INASISTENCIA = "salutem_cita"`
  - `alertas_citas.alertar_inasistencia(db, *, salutem_cita_id: int, cita: Cita, hoy: date, ventanas: dict) -> bool`: crea la alerta si se cumplen todas estas condiciones:
    - la cita está en `inasistencia`;
    - `cita.fecha >= hoy - DIAS_NOVEDAD_INASISTENCIA`;
    - el tipo está activo;
    - la especialidad pasa el filtro de `citas_especialidades_reportes_set` (vacío = todas);
    - no existe ya una alerta de ese tipo para ese `caso_id`, en ningún estado.

    El destinatario es `_resolver_usuario(cita.ingreso_id, db)`. `plazo_objetivo` es la medianoche UTC de `cita.fecha`. Audita la creación.
  - `alertas_citas.resolver_alertas_con_hora(db, hoy: date, actor: str) -> int`: marca como `resuelta` las alertas `control_medico` e `inasistencia` en estado pendiente o leída cuyo paciente tiene hora vigente. Para llegar al paciente: en `control_medico`, por `caso_id` → `ControlMedico.ingreso_id` → `Ingreso.paciente_id`; en `inasistencia`, por `caso_id` → `SalutemCita` → `Cita.salutem_cita_id` → `Ingreso.paciente_id`. Para resolver, seguir el mismo patrón de campos y auditoría que `alertas_control.resolver_alertas_control`. Devuelve cuántas resolvió.
  - Cambio en `_construir_hitos_control_medico`:
    - Tomar el último control por ingreso, solo de ingresos activos.
    - Excluir los `origen='CEPA'` con `proximo_agendado=True`.
    - Excluir a los pacientes con hora vigente, sin importar el origen.
    - `hoy` se recibe como parámetro: `ejecutar_job_alertas` ya lo tiene.
  - `ejecutar_job_alertas` llama a `resolver_alertas_con_hora(db, hoy, actor)` antes de construir los hitos.
  - `sincronizar_citas` llama a `alertar_inasistencia` por cada cita que quede en `inasistencia` (suma a `alertas_inasistencia`) y, al final, a `resolver_alertas_con_hora` (suma a `alertas_resueltas`).

- [ ] **Paso 1: Escribir los tests que fallan**
  - `test_control_salutem_con_hora_vigente_no_alerta`
  - `test_control_salutem_proximo_agendado_sin_hora_si_alerta`
  - `test_control_cepa_proximo_agendado_no_alerta`
  - `test_control_de_ingreso_cerrado_no_alerta`
  - `test_alerta_control_abierta_se_resuelve_al_aparecer_hora`
  - `test_inasistencia_reciente_crea_alerta` (con `caso_tipo="salutem_cita"` y `caso_id=salutem_cita_id`)
  - `test_inasistencia_antigua_no_alerta` (15 días)
  - `test_inasistencia_no_se_duplica_en_segunda_corrida`
  - `test_inasistencia_no_se_repite_tras_resolverla` (resuelta → otra corrida → sigue habiendo una sola)
  - `test_inasistencia_tipo_desactivado_no_alerta`
  - `test_inasistencia_especialidad_fuera_de_filtro_no_alerta` (con monkeypatch de la configuración)
  - `test_inasistencia_se_resuelve_al_aparecer_hora`

- [ ] **Paso 2: Correr y confirmar que fallan.**

- [ ] **Paso 3: Implementar.**

- [ ] **Paso 4: Correr `tests/test_alertas*.py`, `tests/salutem_sync` y `tests/test_alertas_citas.py`, y confirmar que pasan.** Los tests de alertas que ya existían y asumían el criterio anterior de control médico se ajustan al nuevo. Anotar en el reporte cuáles se ajustaron.

- [ ] **Paso 5: Commit**
  `git commit -m "feat(alertas): control médico sin falsas alarmas y alerta de inasistencia desde SALUTEM"`

### Tarea 4: Reportes sobre las citas de SALUTEM

**Archivos:**
- Modificar: `backend/app/services/reportes_filtros.py`, `backend/app/routers/reporte_adherencia.py`, `reporte_operativo.py`, `reporte_convenio.py`, `reporte_carga.py`, `dashboard.py`, `backend/app/schemas/reportes.py`, `frontend/src/features/reportes/ReportesPage.tsx` y `frontend/src/types/api.ts` (regenerado)
- Test: `backend/tests/test_reportes_citas_salutem.py` y los tests de reportes ya existentes que haga falta ajustar

**Interfaces:**
- Produce:
  - `reportes_filtros.condicion_citas_reportables() -> ColumnElement[bool]`: `Cita.origen == "SALUTEM"` y, si el set de especialidades no está vacío, `func.lower(func.trim(Cita.especialidad)).in_(set)`. Usa solo columnas de `Cita`, así que no necesita join.
  - Las 5 consultas de `cita` aplican esa condición.
  - Adherencia: el denominador cuenta solo `estado IN ('realizada','inasistencia')`. Los campos del schema `AdherenciaPaciente` mantienen sus nombres (`citas_agendadas` sigue siendo el denominador) y el docstring explica el criterio.
  - Carga: agrupa por `func.trim(Cita.profesional_nombre)` y `Cita.especialidad`. `CargaProfesionalItem.profesional_id` pasa a `int | None` y se llena con `Cita.profesional_id`. `nombre_profesional` muestra el nombre, o "Sin profesional informado" si es nulo. `total_casos` es la cantidad de ingresos distintos, y `total_atenciones` la de realizadas.
  - Frontend: en la pestaña Carga, mostrar `nombre_profesional` y quitar el respaldo `N° id`. En la pestaña Adherencia, agregar una línea de ayuda debajo del KPI que diga exactamente: "Atendidas sobre el total de citas atendidas más inasistencias. Las anuladas y las futuras no cuentan."

- [ ] **Paso 1: Escribir los tests que fallan**
  - Para cada reporte (adherencia, operativo, convenio, carga y dashboard), un test `test_<reporte>_ignora_citas_origen_sige` (Foco 4).
  - `test_filtro_especialidades_reportes` (con monkeypatch de la configuración).
  - `test_adherencia_excluye_anuladas_y_agendadas`: 2 realizadas, 1 inasistencia, 1 anulada y 1 agendada → `pct_adherencia == 66.67`.
  - `test_adherencia_solo_anuladas_es_none` (Foco 5).
  - `test_carga_agrupa_por_profesional_nombre`: incluye un profesional que no está en el catálogo (con `profesional_id` nulo) y citas sin nombre agrupadas como "Sin profesional informado".

- [ ] **Paso 2: Correr y confirmar que fallan.**

- [ ] **Paso 3: Implementar el backend.** Después, regenerar `api.ts` desde el `openapi.json` local, como en la Fase 1, y verificar que el diff solo toque los schemas de reportes. Luego, el frontend.

- [ ] **Paso 4: Correr la suite completa del backend, más `npx tsc --noEmit -p tsconfig.app.json && npx vitest run src/features/reportes`.**

- [ ] **Paso 5: Commit**
  `git commit -m "feat(reportes): contar solo citas SALUTEM, nueva adherencia y carga por quien atendió"`

### Tarea 5: PATCH de estado protegido, seed y orquestador

**Archivos:**
- Modificar: `backend/app/routers/citas.py`, `backend/app/scripts/seed_dev_data.py` y `backend/app/services/salutem_sync/orquestador.py`
- Test: `backend/tests/test_citas_dd1.py` y `backend/tests/salutem_sync/test_orquestador*.py` (los que ya existen)

**Interfaces:**
- Consume: `sincronizar_citas` (Tarea 2).
- Produce:
  - PATCH `/api/v1/citas/{id}/estado` sobre `origen='SALUTEM'` → 409, con el detalle exacto "El estado de esta cita lo informa SALUTEM".
  - El seed crea las citas con `origen="SALUTEM"` y `salutem_cita_id` ficticio, único y negativo (`-1, -2, …`), para no chocar con ids reales.
  - El orquestador, después de los borradores y en su propio try/except (igual que los borradores), llama a `sincronizar_citas(db, desde=None if modo in _VINCULAN_TODO else ingresos_desde, ahora=ahora())`. Suma sus errores y registra los contadores en el log ("Citas SALUTEM: …").

- [ ] **Paso 1: Escribir los tests que fallan**
  - `test_patch_estado_cita_salutem_409`
  - `test_patch_estado_cita_sige_200`
  - `test_orquestador_corre_paso_de_citas` (modo `caliente` con el stub de SALUTEM: hay una cita importada)
  - `test_orquestador_backfill_revisa_todo` (`desde=None`)
  - `test_fallo_en_citas_no_pierde_el_ciclo` (monkeypatch para que `sincronizar_citas` lance una excepción → la ejecución queda `con_errores`)

- [ ] **Paso 2: Correr y confirmar que fallan.**

- [ ] **Paso 3: Implementar.**

- [ ] **Paso 4: Correr la suite completa y confirmar que pasa.**

- [ ] **Paso 5: Commit**
  `git commit -m "feat(citas): el estado de las citas SALUTEM no se edita a mano; el sync las importa en cada ciclo"`

### Tarea 6: Etiquetas de la alerta de inasistencia en el frontend

**Archivos:**
- Modificar: `frontend/src/components/shell/AlertsPanel.tsx`, `frontend/src/features/config-alertas/api.ts` y `frontend/src/types/api.ts` (el `TipoAlerta` regenerado)
- Test: los tests del panel de alertas y de config-alertas que ya existen, más uno nuevo

**Interfaces:**
- Produce:
  - La etiqueta `inasistencia: "Inasistencia a cita"` en los dos mapas.
  - `inasistencia` en `TIPOS_SIN_DIAS`.
  - En el panel, una alerta `inasistencia` muestra al paciente y enlaza a su ficha, igual que las de control. Si el panel obtiene el paciente a partir de `caso_tipo`, se agrega el caso `salutem_cita` en el backend, siguiendo el mismo mecanismo que use hoy `control_medico`. Anotar en el reporte qué mecanismo era.

- [ ] **Paso 1: Escribir el test que falla:** `muestra "Inasistencia a cita" con el nombre del paciente`.
- [ ] **Paso 2: Correrlo y confirmar que falla.**
- [ ] **Paso 3: Implementar.**
- [ ] **Paso 4:** `npx tsc --noEmit -p tsconfig.app.json && npx eslint src && npx vitest run`, todo en verde.
- [ ] **Paso 5: Commit**
  `git commit -m "feat(alertas): mostrar la alerta de inasistencia a cita"`

### Tarea 7: Verificación y PR

- [ ] **Paso 1:** Compilar con el dialecto Oracle (`.compile(dialect=oracle.dialect())`) las consultas nuevas de `citas_cepa.py`, `alertas_citas.py` y `reportes_filtros.py`, y revisar que no tengan construcciones propias de Postgres.
- [ ] **Paso 2:** Crear una BD de verificación copiando la de desarrollo (`createdb -T cepa cepa_fase2_verif`) y migrar a head. Insertar a mano `salutem_persona` y `salutem_cita` para 2 pacientes del seed: una ATENDIDO, una NO_ASISTE de ayer y una AGENDADO futura. Correr `sincronizar_citas(desde=None)` desde un script de Python y comprobar que existen las filas en `cita` y la alerta de inasistencia.
- [ ] **Paso 3:** Levantar backend y frontend contra esa BD (con `launch.json` y puertos libres). Como Coordinación, revisar en el navegador:
  - la pestaña Carga (nombres de SALUTEM),
  - la adherencia con su texto de ayuda,
  - el panel de alertas ("Inasistencia a cita"),
  - "Umbrales de alerta" (el tipo nuevo con su interruptor).

  Revisar que la consola no tenga errores.
- [ ] **Paso 4:** Limpiar: detener los servidores, quitar las configuraciones temporales de `launch.json` y borrar con `dropdb` las BD `cepa_fase2_verif` y `cepa_test_fase2`.
- [ ] **Paso 5:** Push y abrir el PR contra la base. La descripción debe incluir:
  - un resumen de las decisiones;
  - que los reportes cambian de criterio (adherencia y carga);
  - las 8 preguntas abiertas al CEPA con sus valores por defecto;
  - que la primera carga necesita correr el modo `backfill` del sync en la VM;
  - que hay que validar en Oracle real.
