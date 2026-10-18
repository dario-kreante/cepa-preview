# Pacientes por citar (Fase 1) — Plan de implementación

> **Para agentes:** SUB-SKILL REQUERIDA: usar superpowers:subagent-driven-development (recomendado) o superpowers:executing-plans para implementar este plan tarea por tarea. Los pasos usan checkboxes (`- [ ]`).

**Objetivo:** reemplazar la Agenda de propuestas confirmables por una lista de trabajo calculada en vivo ("Pacientes por citar"), que se cierra sola cuando SALUTEM ya tiene hora para el paciente y registra la gestión de contacto.

**Arquitectura:** la lista no se guarda: se calcula en cada consulta a partir de candidatos ya filtrados por profesional (PR #50), un reparto puro por cupo y feriados en `scheduler.py`, y la exclusión de quienes ya tienen hora vigente en `salutem_cita` (cruce por RUT o `salutem_persona_id`). La gestión de contacto es la única tabla nueva. La generación y la confirmación de propuestas se retiran.

**Stack:** FastAPI + SQLAlchemy 2 (Postgres y Oracle 19c), Alembic, pytest; React + TanStack Query + openapi-fetch, vitest + MSW.

**Spec:** `docs/superpowers/specs/2026-10-16-agenda-lista-de-trabajo-design.md`

## Base de la rama

Crear `claude/agenda-lista-trabajo` desde `origin/claude/agenda-por-profesional` (PR #50, que a su vez parte del #49). Si #49 y #50 ya están mergeados, crearla desde `origin/main`. El PR se abre contra la base de la que partió.

## Restricciones globales

- SQL portable a Postgres y Oracle 19c (D15): nada de `DISTINCT ON` ni funciones propias de un motor; booleanos con `true()`/`false()` de Core.
- Solo lectura sobre SALUTEM (v4 D12). El SIGE nunca escribe `control_medico.proximo_agendado`.
- Migración nueva `1350`, con `down_revision = "1340"`.
- Escritura: roles `Administrativo` y `Coordinacion`. Lectura: además `Auditor`.
- Cada alta o cambio llama a `record_audit` y el commit lo hace el router.
- "Hoy" es `hoy_en_santiago(datetime.now(timezone.utc))` (`app/services/salutem_sync/incremental.py`). Los servicios reciben `hoy: date` por parámetro para poder testearlos.
- Todo el texto visible va en español. La ruta del frontend sigue siendo `/agenda` y el menú dice "Pacientes por citar".
- Tests de backend: `cd backend && uv run pytest`, sobre la BD compartida `cepa_test`. No correr dos suites al mismo tiempo desde dos sesiones.
- Push con la cuenta gh `dario-kreante`.

## Foco de revisión

1. Un paciente cruzado **solo por RUT** (con `salutem_persona_id` nulo) que tiene hora vigente futura no debe aparecer. Es el caso más común en producción. → Test en la Tarea 2.
2. Un paciente que aparece en dos listas (control con A y receta con B): si marca `agendada_en_salutem` con A, se oculta solo en la lista de A. → Test en la Tarea 4.
3. Un rango solo con fin de semana o feriados no debe romper nada: `por_dia` queda vacío y todos van a `sin_cupo`. → Test en la Tarea 1.
4. Un paciente con dos ingresos activos debe mostrar el folio del más reciente, y uno con ingreso egresado no debe aparecer. → Tests en las Tareas 2 y 4.
5. Si alguien marcó "agendada en SALUTEM" pero la hora nunca llega, el paciente vuelve después de 3 días hábiles con la marca `dijo_agendada_sin_hora`. → Test en la Tarea 4.

---

### Tarea 1: Reparto de carga con feriados y sin cupo (scheduler puro)

**Archivos:**
- Modificar: `backend/app/agendamiento/scheduler.py`
- Test: `backend/tests/agendamiento/test_scheduler.py`

**Interfaces:**
- Produce:
  ```python
  @dataclass
  class CargaDia:
      fecha: date
      cupo: int
      asignados: int

  @dataclass
  class Reparto:
      asignados: list[ResultadoCandidato]   # excluida_por is None, fecha_candidata = día sugerido
      en_reposo: list[ResultadoCandidato]   # excluida_por = "reposo vigente hasta AAAA-MM-DD"
      sin_cupo: list[Candidato]             # no cupieron en ningún día hábil del rango
      por_dia: list[CargaDia]               # solo días hábiles no feriados con cupo > 0, en orden

  def repartir_carga(
      candidatos: list[Candidato],
      desde: date,
      hasta: date,
      disponibilidad: list[DisponibilidadDia],
      festivos: frozenset[date] = frozenset(),
  ) -> Reparto
  ```

- [ ] **Paso 1: Escribir los tests que fallan**
  - `test_repartir_carga_salta_feriados`: cupo de 2 el lunes y el martes, el lunes es feriado y hay 3 candidatos → `por_dia` tiene solo el martes, con `asignados=2`; 1 candidato queda en `sin_cupo`.
  - `test_repartir_carga_rango_solo_fin_de_semana`: rango sábado–domingo → `por_dia == []`, `asignados == []` y todos los candidatos en `sin_cupo`.
  - `test_repartir_carga_reposo_en_todo_el_rango_va_a_en_reposo`: el candidato está en reposo todos los días → aparece en `en_reposo` y no en `sin_cupo`.
  - `test_repartir_carga_respeta_prioridad`: con cupo 1, un P3 y un P1 → asignado el P1, el P3 en `sin_cupo`.

- [ ] **Paso 2: Correr y confirmar que fallan**
  Comando: `uv run pytest tests/agendamiento/test_scheduler.py -k repartir -v`
  Esperado: FAIL con `ImportError: cannot import name 'repartir_carga'`.

- [ ] **Paso 3: Implementar `repartir_carga`** en `scheduler.py`, reutilizando `_clave_orden`, `_cupo_para_dia`, `_reposo_vigente_hasta` y `_dias_habiles_en_rango`. Los días en `festivos` quedan sin cupo. La asignación usa el mismo algoritmo de `proponer_agenda_semana`: el primer día con cupo y sin reposo. Si no se asignó y hubo reposo en algún día con cupo, va a `en_reposo`; en cualquier otro caso, a `sin_cupo`. No tocar `proponer_agenda_semana` (se elimina en la Tarea 6).

- [ ] **Paso 4: Correr y confirmar que pasan**
  Comando: `uv run pytest tests/agendamiento/test_scheduler.py -v`
  Esperado: PASS (los tests nuevos y los que ya existían).

- [ ] **Paso 5: Commit**
  `git commit -m "feat(agenda): reparto de carga con feriados y pacientes sin cupo"`

### Tarea 2: Candidatos para la lista y "ya tiene hora en SALUTEM"

**Archivos:**
- Crear: `backend/app/services/salutem_sync/vigencia.py`
- Modificar: `backend/app/services/salutem_sync/controles.py` (`_proxima_cita` pasa a usar la condición compartida)
- Modificar: `backend/app/agendamiento/service.py` (`_cargar_candidatos`)
- Crear: `backend/app/agendamiento/salutem.py`
- Test: `backend/tests/agendamiento/test_lista_candidatos.py`

**Interfaces:**
- Produce:
  - `vigencia.cita_vigente_desde(desde: date) -> ColumnElement[bool]`: `SalutemCita.fecha_cita >= desde AND desaparecida_en IS NULL AND estado_id NOT IN (ANULADO, NO_ASISTE)`. `_proxima_cita` la usa con `fecha_cita > fecha`, así que hay que separar la parte de vigencia (`cita_vigente() -> ColumnElement[bool]`) de la comparación de fecha.
  - `agendamiento.salutem.pacientes_con_hora_vigente(db: Session, paciente_ids: Collection[int], hoy: date) -> set[int]`: cruza `Paciente` con `SalutemPersona` vía `filtro.cruce_con_paciente()` y luego con `SalutemCita.persona_id`.
  - `agendamiento.salutem.pacientes_sin_vinculo(db: Session, paciente_ids: Collection[int]) -> set[int]`: los que no tienen ninguna `SalutemPersona` que cumpla el cruce.
  - `_cargar_candidatos(db, profesional_id, fecha_ini, fecha_fin, hoy: date) -> list[Candidato]`: se agrega `hoy` en reemplazo de `date.today()`.

- [ ] **Paso 1: Escribir los tests que fallan**, creando con helpers propios `Paciente`, `Ingreso`, `ControlMedico`, `SalutemPersona` y `SalutemCita`:
  - `test_hora_vigente_por_rut_sin_persona_id`: el paciente tiene RUT, `salutem_persona_id=None`, y existe una persona con el mismo RUT con una cita AGENDADO para mañana → `pacientes_con_hora_vigente` lo incluye.
  - `test_hora_vigente_por_persona_id`: igual, pero sin RUT y con `salutem_persona_id` → lo incluye.
  - `test_cita_anulada_o_no_asiste_no_cuenta`: estados ANULADO y NO_ASISTE, y una cita con `desaparecida_en` informado → no lo incluye.
  - `test_cita_pasada_no_cuenta`: `fecha_cita = hoy - 1` → no lo incluye.
  - `test_sin_vinculo`: un paciente sin persona que cruce → está en `pacientes_sin_vinculo`.
  - `test_candidatos_ignoran_proximo_agendado_en_controles_salutem`: último control con `origen="SALUTEM"`, `proximo_agendado=True` y vencido → es candidato.
  - `test_candidatos_respetan_proximo_agendado_en_controles_cepa`: `origen="CEPA"` y `proximo_agendado=True` → no es candidato.
  - `test_candidatos_solo_ingreso_activo`: ingresos con `estado="cerrado"` y con `estado="derivado"` (`EstadoCaso.CERRADO`/`DERIVADO`) → no son candidatos.

- [ ] **Paso 2: Correr y confirmar que fallan**
  Comando: `uv run pytest tests/agendamiento/test_lista_candidatos.py -v`
  Esperado: FAIL por imports que todavía no existen.

- [ ] **Paso 3: Implementar.**
  - `vigencia.py` y el refactor de `_proxima_cita`. Su comportamiento no debe cambiar: los tests de `tests/salutem_sync` tienen que seguir en verde.
  - `salutem.py`, con las dos funciones.
  - En `_cargar_candidatos`, agregar `ControlMedico.origen` a `_latest_ctrl`. Reemplazar `proximo_agendado == false()` por `or_(_latest_ctrl.c.origen == "SALUTEM", _latest_ctrl.c.proximo_agendado == false())`. Agregar `Ingreso.estado == EstadoCaso.ACTIVO.value` en las tres consultas (vencidos, próximos y recetas). Usar `hoy` del parámetro. Los llamadores que ya existen pasan `date.today()` hasta la Tarea 6.

- [ ] **Paso 4: Correr y confirmar que pasan**
  Comando: `uv run pytest tests/agendamiento tests/salutem_sync -v`
  Esperado: PASS.

- [ ] **Paso 5: Commit**
  `git commit -m "feat(agenda): detectar hora vigente en SALUTEM y candidatos solo con ingreso activo"`

### Tarea 3: Gestión de contacto (modelo, migración y API)

**Archivos:**
- Crear: `backend/app/agendamiento/gestion.py` (servicio)
- Modificar: `backend/app/agendamiento/models.py`, `enums.py`, `schemas.py` y `router.py`
- Crear: `backend/migrations/versions/1350_gestion_citacion.py`
- Test: `backend/tests/agendamiento/test_gestion_citacion.py`

**Interfaces:**
- Produce:
  - `enums.ResultadoGestion(str, Enum)`: `AGENDADA_EN_SALUTEM="agendada_en_salutem"`, `NO_CONTESTA="no_contesta"`, `RECHAZA="rechaza"`, `OTRO="otro"`.
  - Modelo `GestionCitacion` (tabla `gestion_citacion`) con `id` BigInteger Identity, `paciente_id` BigInteger FK `paciente.id` indexado, `profesional_id` BigInteger FK `profesional.id`, `resultado` String(25), `nota` String(300) nullable, `usuario` String(60), `created_at` DateTime(tz).
  - `gestion.registrar_gestion(db, paciente_id: int, profesional_id: int, resultado: ResultadoGestion, nota: str | None, actor: str, rol: str) -> GestionCitacion`: devuelve 404 si el paciente o el profesional no existen.
  - `gestion.listar_gestiones(db, paciente_id: int) -> list[GestionCitacion]`, de la más reciente a la más antigua.
  - `gestion.ultimas_gestiones(db, paciente_ids: Collection[int]) -> dict[int, GestionCitacion]`: la última de cada paciente, con cualquier profesional, en una sola consulta (subconsulta con `MAX(created_at)`; portable).
  - `gestion.ocultos_por_agendada(db, profesional_id: int, paciente_ids: Collection[int], desde: datetime) -> set[int]`: los pacientes con una gestión `agendada_en_salutem` de **ese profesional** con `created_at >= desde`.
  - Schemas `GestionCreate {profesional_id: int, resultado: ResultadoGestion, nota: str | None (máximo 300, espacios normalizados)}` y `GestionRead`.
  - Endpoints: `POST /api/v1/pacientes-por-citar/{paciente_id}/gestiones` (escritor, 201) y `GET /api/v1/pacientes-por-citar/{paciente_id}/gestiones` (lector).

- [ ] **Paso 1: Escribir los tests que fallan**
  - `test_registrar_gestion_201_y_auditoria`: con `as_admin` → 201; en el cuerpo, `resultado` y `usuario` correctos; existe un `audit_log` con `entity="gestion_citacion"`.
  - `test_registrar_gestion_auditor_403`.
  - `test_registrar_gestion_resultado_invalido_422`.
  - `test_registrar_gestion_paciente_inexistente_404`.
  - `test_listar_gestiones_orden_desc`.
  - `test_ultimas_gestiones_una_por_paciente`.
  - `test_ocultos_por_agendada_es_por_profesional`: `agendada_en_salutem` con el profesional A → el paciente queda oculto para A y no para B.

- [ ] **Paso 2: Correr y confirmar que fallan.**
  Comando: `uv run pytest tests/agendamiento/test_gestion_citacion.py -v`
  Esperado: FAIL.

- [ ] **Paso 3: Implementar el modelo** (registrarlo en `app/models/__init__.py`), **la migración 1350** (`create_table`, con FKs e índice en `paciente_id`; el downgrade hace `drop_table`), **el servicio y los endpoints.**

- [ ] **Paso 4: Correr y confirmar que pasan**, incluida la migración de ida y vuelta:
  Comando: `uv run pytest tests/agendamiento/test_gestion_citacion.py -v && DATABASE_URL=postgresql+psycopg://cepa:cepa@localhost:5432/cepa_test uv run alembic downgrade 1340 && DATABASE_URL=postgresql+psycopg://cepa:cepa@localhost:5432/cepa_test uv run alembic upgrade head`
  Esperado: PASS, y alembic sin errores.

- [ ] **Paso 5: Commit**
  `git commit -m "feat(agenda): registro de gestión de contacto para pacientes por citar"`

### Tarea 4: Lista calculada `GET /api/v1/pacientes-por-citar`

**Archivos:**
- Crear: `backend/app/agendamiento/lista.py`
- Modificar: `backend/app/agendamiento/schemas.py` y `router.py`
- Test: `backend/tests/agendamiento/test_pacientes_por_citar.py`

**Interfaces:**
- Consume: `repartir_carga` (Tarea 1); `_cargar_candidatos`, `_cargar_disponibilidad`, `pacientes_con_hora_vigente` y `pacientes_sin_vinculo` (Tarea 2); `ultimas_gestiones` y `ocultos_por_agendada` (Tarea 3); `config_alertas.cargar_festivos`.
- Produce:
  - `DIAS_HABILES_OCULTO_AGENDADA = 3`, en `lista.py`.
  - `lista.calcular_pacientes_por_citar(db, profesional_id: int, desde: date, hasta: date, hoy: date) -> PacientesPorCitarRead`.
  - Schemas:
    - `CargaDiaRead {fecha, cupo, asignados}`
    - `UltimaGestionRead {fecha: datetime, resultado, usuario, nota}`
    - `PacientePorCitarRead {paciente_id, nombre, folio: str | None, prioridad: PrioridadCita, razon, fecha_objetivo: date | None, dia_sugerido: date | None, seccion: Literal["por_citar","sin_cupo","en_reposo"], reposo_hasta: date | None, sin_vinculo_salutem: bool, dijo_agendada_sin_hora: bool, ultima_gestion: UltimaGestionRead | None}`
    - `PacientesPorCitarRead {profesional_id, desde, hasta, por_dia: list[CargaDiaRead], pacientes: list[PacientePorCitarRead]}`
  - Endpoint `GET /api/v1/pacientes-por-citar?profesional_id=&desde=&hasta=` (lector). Si no se indica, `desde` es hoy y `hasta` es el viernes de la semana siguiente a `desde`. Responde 404 si el profesional no existe, 422 si está inactivo y 422 si `hasta < desde` o el rango supera los 62 días.

**Algoritmo** (la parte que la firma no determina):
1. Calcular los candidatos y quitar a quienes tienen hora vigente en SALUTEM.
2. `inicio_ventana` = el momento que queda `DIAS_HABILES_OCULTO_AGENDADA` días hábiles antes de `hoy`, contando los feriados. Quitar a los que devuelve `ocultos_por_agendada(desde=inicio_ventana)`.
3. A los que tienen como última gestión con este profesional un `agendada_en_salutem` anterior a esa ventana, y siguen sin hora, marcarlos con `dijo_agendada_sin_hora=True`.
4. `repartir_carga` con los feriados.
5. Armar las filas. El folio es el del ingreso activo con `fecha_ingreso` más reciente. Orden: `por_citar` por (`dia_sugerido`, prioridad, `fecha_objetivo`), luego `sin_cupo` por prioridad y al final `en_reposo`.

- [ ] **Paso 1: Escribir los tests que fallan**
  - `test_lista_excluye_paciente_con_hora_vigente_por_rut` (Foco 1, vía API).
  - `test_lista_secciones_y_dia_sugerido`: cupo de 1 el lunes, con un P1 y un P2 → el P1 queda en `por_citar` con `dia_sugerido` = lunes, el P2 en `sin_cupo`; en `por_dia`, el lunes tiene `asignados=1`.
  - `test_lista_oculta_agendada_solo_para_ese_profesional` (Foco 2).
  - `test_lista_vuelve_tras_3_dias_habiles_con_marca` (Foco 5): la gestión `agendada_en_salutem` tiene `created_at` de hace 4 días hábiles y no hay hora → el paciente aparece con `dijo_agendada_sin_hora=True`; si es de hace 1 día hábil, no aparece.
  - `test_lista_folio_del_ingreso_activo_mas_reciente` (Foco 4).
  - `test_lista_marca_sin_vinculo_salutem`.
  - `test_lista_profesional_inexistente_404_e_inactivo_422`.
  - `test_lista_rango_por_defecto_hasta_viernes_siguiente`.
  - `test_lista_auditor_puede_leer` y `test_lista_sin_token_401`.

- [ ] **Paso 2: Correr y confirmar que fallan.**
  Comando: `uv run pytest tests/agendamiento/test_pacientes_por_citar.py -v`
  Esperado: FAIL.

- [ ] **Paso 3: Implementar** `lista.py`, los schemas y el endpoint. El router calcula `hoy` según las restricciones globales.

- [ ] **Paso 4: Correr y confirmar que pasan.**
  Comando: `uv run pytest tests/agendamiento -v`
  Esperado: PASS.

- [ ] **Paso 5: Commit**
  `git commit -m "feat(agenda): lista calculada de pacientes por citar"`

### Tarea 5: Disponibilidad con reemplazo y baja

**Archivos:**
- Modificar: `backend/app/agendamiento/service.py` (`crear_disponibilidad`) y `router.py`
- Test: `backend/tests/agendamiento/test_agendamiento_api.py`

**Interfaces:**
- Produce:
  - `crear_disponibilidad(...)`: misma firma que hoy. Si existe una fila activa para (profesional, día), se actualiza su cupo y se audita con `UPDATE`; si no, se crea con `CREATE`.
  - `DELETE /api/v1/disponibilidad-profesional/{id}` (escritor): marca la fila con `activo=False` y responde 204, o 404 si no existe.

- [ ] **Paso 1: Escribir los tests que fallan**
  - `test_disponibilidad_mismo_dia_reemplaza`: dos POST para el lunes con cupos 3 y 5 → el GET devuelve una sola fila, con cupo 5.
  - `test_disponibilidad_delete_la_saca_del_listado`.
  - `test_disponibilidad_delete_auditor_403`.

- [ ] **Paso 2: Correr y confirmar que fallan.**
  Comando: `uv run pytest tests/agendamiento/test_agendamiento_api.py -k disponibilidad -v`
  Esperado: FAIL.

- [ ] **Paso 3: Implementar.**

- [ ] **Paso 4: Correr y confirmar que pasan.**
  Mismo comando del Paso 2.
  Esperado: PASS.

- [ ] **Paso 5: Commit**
  `git commit -m "fix(agenda): la disponibilidad reemplaza el día en vez de duplicarlo y se puede quitar"`

### Tarea 6: Retirar generación y confirmación de propuestas

**Archivos:**
- Modificar: `backend/app/agendamiento/router.py`, `service.py`, `scheduler.py` y `schemas.py`
- Modificar o eliminar tests: `backend/tests/agendamiento/test_agendamiento_api.py`, `test_agendamiento_service.py`, `test_scheduler.py`, `test_agendamiento_rendimiento.py` y `test_agendamiento_schemas.py`. En `backend/tests/test_citas_dd1.py`, los casos TC-DD1-01 y TC-DD1-04 parten de `confirmar_citas`: se eliminan los que prueban la confirmación, y el flujo de PATCH de estado y su efecto en el reporte operativo se conserva creando las filas `Cita` directamente.

**Interfaces:**
- Elimina: `POST /api/v1/propuestas-agenda`, `POST /api/v1/propuestas-agenda/{id}/confirmar`, `generar_propuesta`, `confirmar_citas`, `_ingreso_activo_para_paciente`, `proponer_agenda`, `proponer_agenda_semana` y `GenerarPropuestaRequest`/`ConfirmarCitasRequest`.
- Se mantienen: los GET de propuestas y citas (historial), los modelos y las tablas. También `PATCH /api/v1/citas/{id}/estado`.

- [ ] **Paso 1: Escribir el test que falla**
  `test_generar_y_confirmar_propuesta_retirados`: el POST a ambas rutas responde 404 o 405.

- [ ] **Paso 2: Correr y confirmar que falla.**

- [ ] **Paso 3: Eliminar el código y los tests que solo cubrían lo retirado.** El test de rendimiento (si sirve) se reescribe sobre `calcular_pacientes_por_citar`. Al final, `grep -rn "generar_propuesta\|confirmar_citas\|proponer_agenda" backend/app` no debe encontrar nada.

- [ ] **Paso 4: Correr la suite completa del backend.**
  Comando: `uv run pytest -p no:warnings -q`
  Esperado: todo pasa, sin errores de import.

- [ ] **Paso 5: Commit**
  `git commit -m "refactor(agenda): retirar la propuesta confirmable; SALUTEM es la agenda real"`

### Tarea 7: Pantalla "Pacientes por citar"

**Archivos:**
- Modificar: `frontend/src/types/api.ts`, regenerado desde el `openapi.json` del backend local (`app.openapi()` → `npx openapi-typescript <archivo> -o src/types/api.ts`). Revisar que el diff solo toque lo de agenda.
- Reescribir: `frontend/src/features/agenda/api.ts`, `hooks.ts` y `AgendaPage.tsx`
- Crear: `frontend/src/features/agenda/RegistrarContactoDialog.tsx`
- Eliminar: `frontend/src/features/agenda/propuestaSchema.ts`
- Modificar: `frontend/src/app/shell/nav.ts` (etiqueta "Pacientes por citar" y su título/breadcrumb para `/agenda`)
- Test: `frontend/src/features/agenda/hooks.test.tsx` y crear `AgendaPage.test.tsx`

**Interfaces:**
- Consume: los endpoints de las Tareas 3, 4 y 5; `useProfesionales(true)` de `features/profesionales/hooks`.
- Produce los hooks:
  - `usePacientesPorCitar(profesionalId: number | null, rango: "semana" | "dos_semanas" | "mes")`. "semana" va de hoy al viernes de esta semana; "dos_semanas" usa el valor por defecto del backend; "mes" va hasta el último día del mes.
  - `useRegistrarGestion()`, que invalida `["agenda","por-citar"]`.
  - `useGestiones(pacienteId)`.
  - `useDisponibilidad`, `useCrearDisponibilidad` y `useQuitarDisponibilidad`.

**Pantalla** (seguir el estilo de las pantallas que ya existen):
- Arriba: selector de profesional (el de hoy) y selector de rango.
- Franja de carga con chips `Lun 14 · 3/4`.
- Tabla "Por citar" con las columnas: paciente y folio, prioridad (badge + razón), fecha objetivo, día sugerido, último contacto ("No contesta · 15-10 · cvidal") y el botón "Registrar contacto". Las marcas "Sin vínculo SALUTEM" y "Dijo agendada, sin hora en SALUTEM" van como badges.
- Secciones plegables "Sin cupo en el período (N)" y "En reposo (N)".
- Tarjeta plegable de disponibilidad con un botón para quitar cada día.
- `RegistrarContactoDialog`: un select con los 4 resultados ("Agendada en SALUTEM", "No contesta", "Rechaza", "Otro") y una nota opcional de hasta 300 caracteres. Al guardar muestra el toast "Contacto registrado".
- Si el profesional no tiene disponibilidad, se muestra el aviso "Este profesional no tiene disponibilidad cargada: todos sus pacientes aparecen como sin cupo."
- Los botones de escritura solo aparecen si `puedeEscribir(rol)`.

- [ ] **Paso 1: Escribir los tests que fallan (vitest + MSW)**
  - Hook: `usePacientesPorCitar` envía `profesional_id` y no hace la consulta si es `null`.
  - Pantalla: al elegir un profesional se muestran las filas de `por_citar` y el contador de "Sin cupo en el período (1)".
  - Pantalla: registrar un contacto hace POST con `{profesional_id, resultado: "no_contesta", nota}`.
  - Pantalla: como Auditor no aparece "Registrar contacto".

- [ ] **Paso 2: Correr y confirmar que fallan.**
  Comando: `cd frontend && npx vitest run src/features/agenda`
  Esperado: FAIL.

- [ ] **Paso 3: Implementar.**

- [ ] **Paso 4: Correr y confirmar que todo pasa.**
  Comando: `npx tsc --noEmit -p tsconfig.app.json && npx eslint src && npx vitest run`
  Esperado: sin errores; ESLint sin errores nuevos.

- [ ] **Paso 5: Commit**
  `git commit -m "feat(agenda): pantalla Pacientes por citar con registro de contacto"`

### Tarea 8: Verificación en el navegador y PR

- [ ] **Paso 1:** Crear una BD de verificación copiando la de desarrollo (`createdb -T cepa cepa_porcitar_verif`), migrar a head y simular datos: un control SALUTEM vencido con médico del catálogo, una `salutem_persona` con el mismo RUT y una `salutem_cita` AGENDADO futura para otro paciente. Levantar backend y frontend con `.claude/launch.json` en puertos libres (por ejemplo 8010 y 5174, con `CORS_ORIGINS` y `VITE_API_BASE_URL`).
- [ ] **Paso 2:** Probar el flujo como `cvidal` (Administrativo, contraseña del seed): elegir un profesional → ver la lista y la carga por día; el paciente con hora no aparece; registrar "Agendada en SALUTEM" → el paciente desaparece; quitar un día de disponibilidad → sus pacientes pasan a "Sin cupo". Revisar que la consola no tenga errores.
- [ ] **Paso 3:** Compilar con el dialecto Oracle (`.compile(dialect=oracle.dialect())`) las consultas nuevas de `salutem.py`, `gestion.py` y `lista.py`, y revisar que no usen funciones propias de Postgres.
- [ ] **Paso 4:** Limpiar: detener los servidores, quitar las configuraciones temporales de `launch.json` y hacer `dropdb cepa_porcitar_verif`.
- [ ] **Paso 5:** Push y abrir el PR contra la base de la rama. En la descripción, indicar que adherencia, operativo, convenio, carga y dashboard dejan de recibir citas nuevas hasta la Fase 2, y listar las hipótesis que hay que validar en el periodo de pruebas.
