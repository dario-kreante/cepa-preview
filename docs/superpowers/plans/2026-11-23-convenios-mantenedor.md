# Mantenedor de convenios espejo de SALUTEM — plan de implementación

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** catálogo de convenios sincronizado desde SALUTEM, administrable en Configuración, con selector precargado en la ficha de ingreso y en el reporte Convenio.

**Architecture:** tabla `convenio` alimentada por `GET /financiadores` (tipo CONVENIO) en el modo frío del sync y con un botón. El ingreso sigue guardando el nombre como texto en `Ingreso.tipo_convenio` (ampliado a 120), validado contra el catálogo. La sugerencia sale de `salutem_persona.contenido["origen"]`.

**Tech Stack:** FastAPI, SQLAlchemy 2, Alembic (Oracle 19c en producción, Postgres en tests), pytest; React + TypeScript, TanStack Query, openapi-fetch, Vitest + MSW.

**Spec:** `docs/superpowers/specs/2026-11-23-convenios-mantenedor-design.md`

## Global Constraints

- Migración `1500`, `down_revision = "1490"`. Antes de crearla y antes de mergear: `git fetch` y `git ls-tree origin/main backend/migrations/versions/`; `uv run alembic heads` debe mostrar una sola cabeza.
- Tests backend con BD propia: `TEST_DATABASE_URL=postgresql+psycopg://cepa:cepa@localhost:5432/cepa_test_convenios` (crearla si no existe). `pytest -q` no imprime resumen: mirar el código de salida.
- Normalización de nombres: `normalizar_nombre` de `app/services/salutem_sync/profesionales.py` (sin tildes, `casefold`, espacios colapsados). No duplicarla.
- Roles: leen `Administrativo`, `Coordinacion`, `Auditor`; escriben `Coordinacion`, `Administrativo`.
- Largos: `convenio.nombre` y `Ingreso.tipo_convenio` = 120.
- Nunca se borra un convenio. `visible` solo lo cambia el CEPA; el sync no lo toca, salvo al crear «Sin Convenio» (nace con `visible = false`).
- Textos de la interfaz en español.
- Tipos del frontend: regenerar `frontend/src/types/api.ts` desde el backend local (ver Task 6), no desde staging (retirado).

## Review Focus

1. `origen` y catálogo difieren en mayúsculas o tildes («Convenio ISL Maule» frente a «Convenio ISL MAULE»): la sugerencia debe encontrar el convenio. → test en Task 4.
2. SALUTEM no responde al pulsar «Actualizar desde SALUTEM»: responde 502 con mensaje y no cambia nada. → test en Task 4.
3. Paciente sin persona en SALUTEM, borrador sin RUT o RUT mal escrito: `sugerido` devuelve `null`, nunca un error. → tests en Task 4.
4. Editar un ingreso cuyo `tipo_convenio` antiguo ya no está en el catálogo, sin tocarlo: se guarda sin error. → test en Task 5.
5. Correr el sync dos veces seguidas no crea duplicados ni cambia nada la segunda vez. → test en Task 3.

---

### Task 1: Modelo `Convenio`, migración 1500 y `tipo_convenio` de 120

**Files:**
- Create: `backend/app/models/convenio.py`
- Modify: `backend/app/models/__init__.py` (exportar `Convenio`)
- Modify: `backend/app/models/ingreso.py:68` (`String(40)` → `String(120)`)
- Create: `backend/migrations/versions/1500_convenio.py`
- Test: `backend/tests/test_convenio_model.py`

**Interfaces:**
- Produces: `Convenio` con `id: int`, `nombre: str`, `nombre_normalizado: str` (único), `salutem_id: int | None` (único), `activo_salutem: bool` (default `True`), `visible: bool` (default `True`), `sincronizado_en: datetime | None`, `created_at`, `updated_at`; propiedad `seleccionable: bool` = `visible and (salutem_id is None or activo_salutem)`.

- [ ] **Step 1: Write the failing tests**

```python
def test_convenio_seleccionable_segun_visible_y_salutem(db_session):
    manual = Convenio(nombre="Convenio Rangers", nombre_normalizado="convenio rangers")
    inactivo = Convenio(nombre="Proyecto ISL Biobío", nombre_normalizado="proyecto isl biobio",
                        salutem_id=1662, activo_salutem=False)
    oculto = Convenio(nombre="Sin Convenio", nombre_normalizado="sin convenio",
                      salutem_id=1415, visible=False)
    db_session.add_all([manual, inactivo, oculto]); db_session.flush()
    assert manual.seleccionable is True
    assert inactivo.seleccionable is False
    assert oculto.seleccionable is False

def test_nombre_normalizado_es_unico(db_session):
    db_session.add(Convenio(nombre="A", nombre_normalizado="a")); db_session.flush()
    db_session.add(Convenio(nombre="a", nombre_normalizado="a"))
    with pytest.raises(IntegrityError):
        db_session.flush()

def test_tipo_convenio_acepta_120_caracteres(db_session, ingreso_fixture):
    ingreso_fixture.tipo_convenio = "x" * 120
    db_session.flush(); db_session.refresh(ingreso_fixture)
    assert len(ingreso_fixture.tipo_convenio) == 120
```

- [ ] **Step 2: Run** `uv run pytest tests/test_convenio_model.py -v` → FAIL (`Convenio` no existe).
- [ ] **Step 3: Implement** el modelo (estilo de `app/models/profesional.py`: `Identity(always=False)`, `_utcnow`, `UniqueConstraint` con nombre `uq_convenio_nombre_norm` y `uq_convenio_salutem_id`) y la migración 1500: `create_table("convenio", …)` + `alter_column("ingreso", "tipo_convenio", type_=sa.String(120), existing_type=sa.String(40))`. El downgrade borra la tabla y vuelve a 40 (truncar antes con `UPDATE … SUBSTR` para Oracle). Docstring de la migración en el estilo de `1490`.
- [ ] **Step 4: Run** `uv run pytest tests/test_convenio_model.py tests/test_ingreso_model.py -v` → PASS, y `uv run alembic heads` → una cabeza (`1500`).
- [ ] **Step 5: Commit** `feat(convenios): tabla convenio y tipo_convenio de 120 (migración 1500)`

### Task 2: Cliente SALUTEM — `listar_convenios()`

**Files:**
- Modify: `backend/app/integrations/salutem/models.py` (nuevo `ConvenioSalutem`)
- Modify: `backend/app/integrations/salutem/protocol.py` (método en `SalutemClientProtocol`)
- Modify: `backend/app/integrations/salutem/client.py` (stub y HTTP)
- Modify: `backend/tests/salutem_falso.py` (`SalutemFalso.listar_convenios`, con una lista `convenios` configurable que por defecto está vacía)
- Test: `backend/tests/test_salutem_http_client.py`

**Interfaces:**
- Produces: `ConvenioSalutem(salutem_id: int, nombre: str, activo: bool)` (frozen, `desde_api(d)` lee `id`, `nombre`, `activo`); `SalutemClientProtocol.listar_convenios(self) -> list[ConvenioSalutem]`. El stub devuelve `[]`.

- [ ] **Step 1: Write the failing tests** (con el `_cliente(handler)` y `httpx.MockTransport` que ya usa el archivo)

```python
def test_listar_convenios_filtra_tipo_convenio():
    def handler(req):
        assert req.url.path.endswith("/financiadores")
        return httpx.Response(200, json={"estado": True, "respuesta": [
            {"id": 1486, "nombre": "Convenio Colegio Inglés", "tipo": "CONVENIO", "activo": True},
            {"id": 1173, "nombre": "PARTICULAR", "tipo": "FINANCIADOR", "activo": True},
            {"id": 1662, "nombre": "Proyecto ISL Biobío", "tipo": "CONVENIO", "activo": False},
        ]})
    r = _cliente(handler).listar_convenios()
    assert [(c.salutem_id, c.nombre, c.activo) for c in r] == [
        (1486, "Convenio Colegio Inglés", True), (1662, "Proyecto ISL Biobío", False)]

def test_stub_listar_convenios_vacio():
    assert SalutemStubClient().listar_convenios() == []
```

- [ ] **Step 2: Run** `uv run pytest tests/test_salutem_http_client.py -k convenios -v` → FAIL.
- [ ] **Step 3: Implement** `listar_convenios` con `self._get("financiadores", {})`, ignorando filas que no sean dict o sin `id`/`nombre`.
- [ ] **Step 4: Run** el mismo comando → PASS.
- [ ] **Step 5: Commit** `feat(salutem): lee el catálogo de convenios de /financiadores`

### Task 3: Servicio `sincronizar_convenios` y paso en el modo frío

**Files:**
- Create: `backend/app/services/convenios_sync.py`
- Modify: `backend/app/services/salutem_sync/orquestador.py` (después del bloque de profesionales, solo si `modo == "fria"`)
- Test: `backend/tests/salutem_sync/test_convenios_sync.py` y un caso en `backend/tests/salutem_sync/test_orquestador.py`

**Interfaces:**
- Consumes: `Convenio` (Task 1), `SalutemClientProtocol.listar_convenios` (Task 2), `normalizar_nombre`, `record_audit`, `ACTOR` de `alertas_control`.
- Produces: `ResultadoConvenios(creados: int, actualizados: int, desactivados: int, renombrados: int, ingresos_renombrados: int, errores: list[str])` y `sincronizar_convenios(db: Session, cliente: SalutemClientProtocol, ahora: datetime, actor: str = ACTOR) -> ResultadoConvenios`. No hace commit; si `listar_convenios` lanza `SalutemUnavailableError`, la deja propagar sin tocar nada.

Reglas (del spec): emparejar por `salutem_id`; si no, adoptar un manual con el mismo `nombre_normalizado`; crear los nuevos (`nombre_normalizado == "sin convenio"` nace con `visible=False`); actualizar `nombre`, `nombre_normalizado`, `activo_salutem` y `sincronizado_en`; los que tienen `salutem_id` y no vinieron pasan a `activo_salutem=False`; nunca tocar `visible` de uno existente. Renombre: `UPDATE ingreso SET tipo_convenio = :nuevo WHERE tipo_convenio = :anterior` y **un** `record_audit(action="convenio_renombrado", entity="convenio", entity_id=str(id), valor_anterior=anterior, valor_nuevo=f"{nuevo} ({n} ingresos)")`. Choque del nombre nuevo con otro convenio: no se actualiza ese convenio, error `"convenio {salutem_id}: el nombre «{nuevo}» ya existe"`. Las altas se auditan con `action="convenio_creado"`.

- [ ] **Step 1: Write the failing tests** (cliente: `SalutemFalso` de `tests/salutem_falso.py` con `convenios` cargados; para el caso caído, una subclase cuyo `listar_convenios` lanza `SalutemUnavailableError`)

```python
def test_crea_convenios_y_sin_convenio_nace_oculto(db_session): ...
    # entra: Colegio Inglés (1486, activo), Sin Convenio (1415, activo)
    # assert r.creados == 2; Colegio Inglés visible; Sin Convenio visible is False

def test_adopta_manual_por_nombre_sin_tildes_ni_mayusculas(db_session): ...
    # existe manual "convenio colegio ingles" sin salutem_id → queda con salutem_id=1486, r.creados == 0

def test_no_toca_visible_de_uno_existente(db_session): ...
    # existente 1486 con visible=False → sigue False tras el sync

def test_desactiva_el_que_ya_no_viene(db_session): ...
    # existente 1237 que no viene → activo_salutem False, r.desactivados == 1; el manual sin salutem_id no cambia

def test_renombre_arrastra_ingresos_y_audita_una_vez(db_session, ingreso_fixture): ...
    # convenio 1345 "Convenio ISL MAULE", ingreso con ese tipo_convenio; llega "Convenio ISL Maule"
    # → ingreso.tipo_convenio == "Convenio ISL Maule"; r.ingresos_renombrados == 1
    # → exactamente 1 AuditLog action="convenio_renombrado"

def test_renombre_que_choca_se_salta_y_se_informa(db_session): ...
    # manual "Convenio Rangers"; 1500 llega renombrado a "Convenio RANGERS" → sin cambio, 1 error con "ya existe"

def test_segunda_pasada_no_cambia_nada(db_session): ...
    # sync dos veces con la misma lista → segunda: creados == actualizados == desactivados == 0

def test_salutem_caido_propaga_y_no_cambia_nada(db_session): ...
    # cliente que lanza SalutemUnavailableError → pytest.raises; Convenio count sin cambios
```

Cada test arma su estado y afirma exactamente lo del comentario. En `test_orquestador.py`: el modo `fria` crea los convenios del falso y el modo `caliente` no.

- [ ] **Step 2: Run** `uv run pytest tests/salutem_sync/test_convenios_sync.py -v` → FAIL.
- [ ] **Step 3: Implement** `sincronizar_convenios`. En el orquestador: bloque `try/except` propio como el de profesionales (`log.exception`, `db.rollback()`, error `f"convenios: {type(e).__name__}: {e}"`), solo para `modo == "fria"`, usando el `cliente` que ya recibe `correr`.
- [ ] **Step 4: Run** `uv run pytest tests/salutem_sync tests/test_salutem_no_escribe.py -v` → PASS.
- [ ] **Step 5: Commit** `feat(convenios): sincroniza el catálogo de SALUTEM en el modo frío`

### Task 4: API `/api/v1/convenios`

**Files:**
- Create: `backend/app/schemas/convenio.py`, `backend/app/services/convenios.py`, `backend/app/routers/convenios.py`
- Modify: `backend/app/main.py` (`include_router`)
- Test: `backend/tests/test_convenios_api.py`

**Interfaces:**
- Consumes: Tasks 1–3, `get_salutem_client`, `normalizar_rut` y `RutInvalidoError` de `app/util/rut.py` (un RUT inválido da `null`, no 422).
- Produces:
  - `ConvenioRead {id, nombre, salutem_id: int|None, activo_salutem, visible, seleccionable, sincronizado_en}`; `ConvenioCreate {nombre: str}` (sin espacios sobrantes, 1–120); `ConvenioUpdate {visible: bool|None, nombre: str|None}`; `ActualizacionConvenios {creados, actualizados, desactivados, errores: list[str]}`; `ConvenioSugerido {convenio: ConvenioRead | None}`.
  - `GET /api/v1/convenios?solo_seleccionables=false` → `list[ConvenioRead]` ordenada por nombre.
  - `GET /api/v1/convenios/para-reportes` → `list[str]`: nombres de todo el catálogo más los `ingreso.tipo_convenio` distintos no vacíos que no estén en él, sin repetir, ordenados.
  - `POST /api/v1/convenios` → 201; 409 si el `nombre_normalizado` existe. Audita `convenio_creado`.
  - `PATCH /api/v1/convenios/{id}` → `nombre` en uno con `salutem_id` da 422 («se renombra en SALUTEM»); 404 si no existe; 409 si choca. Audita.
  - `POST /api/v1/convenios/actualizar-salutem` → `ActualizacionConvenios`; `SalutemUnavailableError` → 502 «SALUTEM no respondió; intenta más tarde.» con rollback.
  - `GET /api/v1/convenios/sugerido?paciente_id=…` o `?rut=…` → `ConvenioSugerido`. Persona: por `Paciente.salutem_persona_id`, si no por RUT normalizado en `SalutemPersona.rut`. Sin persona, RUT inválido, `origen` vacío, «Sin Origen» o sin pareja seleccionable → `{convenio: null}`.
  - Función de servicio reutilizable: `convenio_sugerido(db, *, paciente_id: int | None, rut: str | None) -> Convenio | None`.

- [ ] **Step 1: Write the failing tests**

```python
def test_listar_lo_ven_los_tres_roles(as_auditor): ...            # 200
def test_auditor_no_puede_crear(as_auditor): ...                  # POST → 403
def test_crear_duplicado_por_tildes_409(as_admin): ...            # "Convenio Inglés" y "convenio ingles" → 409
def test_no_se_renombra_uno_de_salutem(as_admin, db_session): ... # PATCH nombre en salutem_id=1486 → 422
def test_ocultar(as_coordinacion, db_session): ...                # PATCH visible False → seleccionable False
def test_actualizar_salutem_ok(as_admin, monkeypatch): ...        # cliente falso con 1 convenio → creados == 1
def test_actualizar_salutem_caido_502(as_admin, monkeypatch): ... # → 502, catálogo vacío
def test_para_reportes_incluye_valores_antiguos(as_admin, db_session, ingreso_fixture): ...
    # catálogo "Convenio SSM" + ingreso con "ISL" → ["Convenio SSM", "ISL"]
def test_sugerido_por_paciente_ignora_mayusculas(as_admin, db_session): ...
    # SalutemPersona(origen "Convenio ISL Maule"), Paciente.salutem_persona_id, convenio "Convenio ISL MAULE" → ese convenio
def test_sugerido_por_rut(as_admin, db_session): ...              # persona con rut, sin paciente → convenio
def test_sugerido_sin_origen_es_null(as_admin, db_session): ...   # "Sin Origen" → null
def test_sugerido_rut_invalido_o_sin_persona_es_null(as_admin): ...  # rut="abc" y rut válido sin persona → 200, null
def test_sugerido_convenio_oculto_es_null(as_admin, db_session): ... # pareja con visible False → null
```

`monkeypatch.setattr("app.routers.convenios.get_salutem_client", lambda: Cliente())`, como en `test_documentos_salutem_paciente_api.py`.

- [ ] **Step 2: Run** `uv run pytest tests/test_convenios_api.py -v` → FAIL.
- [ ] **Step 3: Implement** router (`_lector = require_role("Coordinacion", "Administrativo", "Auditor")`, `_escritor = require_role("Coordinacion", "Administrativo")`; declarar `/para-reportes`, `/sugerido` y `/actualizar-salutem` antes de `/{convenio_id}`), servicio y esquemas.
- [ ] **Step 4: Run** el mismo comando → PASS.
- [ ] **Step 5: Commit** `feat(convenios): API del mantenedor, actualización y sugerencia`

### Task 5: Validar `tipo_convenio` en el alta y la edición del ingreso

**Files:**
- Modify: `backend/app/schemas/ingreso.py` (`tipo_convenio` en `IngresoUpdate` y en `IngresoRead`; blanco → `None` con `_texto_o_none` en `IngresoCreate` e `IngresoUpdate`)
- Modify: `backend/app/services/ingreso.py` (`crear_ingreso`, `actualizar_ingreso`)
- Modify: `backend/tests/test_ingreso_dims_dd3.py` (sembrar un `Convenio` «DIEP» antes del POST)
- Test: `backend/tests/test_ingreso_convenio.py`

**Interfaces:**
- Consumes: `Convenio.seleccionable` (Task 1).
- Produces: `validar_tipo_convenio(db, nuevo: str | None, actual: str | None) -> None` en `app/services/convenios.py`. Acepta `None`, `nuevo == actual` o el `nombre` exacto de un convenio seleccionable; si no, `HTTPException(422, "El convenio «{nuevo}» no está en el catálogo de convenios.")`.

- [ ] **Step 1: Write the failing tests** (payload como `_payload` de `test_ingreso_programa.py`)

```python
def test_alta_con_convenio_del_catalogo(as_admin, db_session): ...       # 201, tipo_convenio devuelto
def test_alta_con_convenio_desconocido_422(as_admin): ...                 # "Inventado" → 422
def test_alta_con_convenio_oculto_422(as_admin, db_session): ...          # visible False → 422
def test_alta_sin_convenio_y_blanco_quedan_null(as_admin): ...            # omitido y "  " → None
def test_editar_cambia_convenio(as_admin, db_session, ingreso_fixture): ...  # PATCH válido → 200
def test_editar_conserva_valor_antiguo(as_admin, ingreso_fixture): ...
    # ingreso con "ISL" (fuera del catálogo); PATCH {"tipo_convenio": "ISL", "diagnostico": "x"} → 200
def test_editar_a_valor_desconocido_422(as_admin, ingreso_fixture): ...
```

- [ ] **Step 2: Run** `uv run pytest tests/test_ingreso_convenio.py -v` → FAIL.
- [ ] **Step 3: Implement**: llamar `validar_tipo_convenio` en `crear_ingreso` (con `actual=None`) y en `actualizar_ingreso` solo si `tipo_convenio` viene en `exclude_unset`.
- [ ] **Step 4: Run** toda la suite: `uv run pytest` (exit 0). Si falla algún test que manda `tipo_convenio` libre por la API, sembrar el convenio en ese test; no aflojar la validación.
- [ ] **Step 5: Commit** `feat(ingresos): el convenio del ingreso se valida contra el catálogo`

### Task 6: Frontend — tipos, API y pantalla «Convenios»

**Files:**
- Modify: `frontend/src/types/api.ts` (regenerado)
- Create: `frontend/src/features/convenios/api.ts`, `hooks.ts`, `ConveniosPage.tsx`, `ConveniosPage.test.tsx`
- Modify: `frontend/src/app/router.tsx` (ruta `/convenios`), `frontend/src/app/shell/nav.ts` (ítem en Administración tras Profesionales, ícono `Handshake`, roles `["Coordinacion", "Administrativo"]`; entradas de título y miga «Inicio · Administración · Convenios»), `frontend/src/features/configuracion/ConfiguracionPage.tsx` (descripción «Convenios de la Unidad Clínica; se actualizan desde SALUTEM.»)

**Interfaces:**
- Consumes: endpoints de Task 4.
- Produces: `listarConvenios(soloSeleccionables?: boolean)`, `crearConvenio(body)`, `actualizarConvenio(id, body)`, `actualizarDesdeSalutem()`, `conveniosParaReportes()`, `convenioSugerido(q: {paciente_id?: number; rut?: string})`; hooks `useConvenios(soloSeleccionables = false)`, `useCrearConvenio()`, `useActualizarConvenio()`, `useActualizarDesdeSalutem()`, `useConveniosParaReportes()`, `useConvenioSugerido(q | null)` (deshabilitado con `null`). Clave de query `["convenios"]`. Mismo patrón que `features/profesionales`.

- [ ] **Step 1: Regenerar tipos**: en `backend/`, `uv run python -c "import json; from app.main import app; print(json.dumps(app.openapi()))" > /tmp/openapi-convenios.json`; en `frontend/`, `npx openapi-typescript /tmp/openapi-convenios.json -o src/types/api.ts`. Revisar que el diff solo agregue lo de convenios e ingreso.
- [ ] **Step 2: Write the failing tests** (MSW como `ProfesionalesPage.test.tsx`)

```tsx
it("lista convenios con origen, estado en SALUTEM y visible")      // filas «SALUTEM»/«SIGE», «Activo»/«Inactivo»/«—»
it("Actualizar desde SALUTEM muestra el resultado")                 // toast con «1 nuevo»
it("si SALUTEM falla muestra el mensaje del 502")
it("agregar un convenio manual avisa que conviene crearlo en SALUTEM")
it("409 al agregar muestra «Ya existe un convenio con ese nombre.»")
it("desmarcar Visible llama PATCH {visible:false}")
it("un convenio de SALUTEM no ofrece renombrar")
```

- [ ] **Step 3: Run** `npx vitest run src/features/convenios` → FAIL.
- [ ] **Step 4: Implement** `api.ts`, `hooks.ts` y `ConveniosPage` (maqueta del spec; «Última actualización» = el `sincronizado_en` más reciente).
- [ ] **Step 5: Run** `npx vitest run src/features/convenios src/features/configuracion src/app` y `npx tsc --noEmit -p .` → PASS.
- [ ] **Step 6: Commit** `feat(convenios): pantalla de convenios en Configuración`

### Task 7: Frontend — selector «Convenio» en la ficha de ingreso

**Files:**
- Create: `frontend/src/features/convenios/ConvenioSelect.tsx`, `ConvenioSelect.test.tsx`
- Modify: `frontend/src/features/ingresos/AltaIngresoPage.tsx`, `ingresoSchema.ts` (`tipo_convenio: z.string().optional()`), `EditarFichaDialog.tsx`
- Test: los tests existentes de `AltaIngresoPage` y `PatientSheet.edicion.test.tsx`

**Interfaces:**
- Consumes: `useConvenios(true)`, `useConvenioSugerido` (Task 6).
- Produces: `ConvenioSelect({ id, value, onChange, valorGuardado?: string | null, sugerencia?: { paciente_id?: number; rut?: string } | null })`. Opciones: «Sin convenio» (`""`), los seleccionables y, si `valorGuardado` no está entre ellos, ese valor al final. Con `sugerencia` y `value === ""` mientras el usuario no haya tocado el campo, aplica el sugerido y muestra «Sugerido desde SALUTEM». El envío convierte `""` en `null`.

- [ ] **Step 1: Write the failing tests**

```tsx
it("muestra Sin convenio y los convenios seleccionables")
it("con valor guardado fuera del catálogo lo muestra y lo conserva")
it("precarga el sugerido y muestra «Sugerido desde SALUTEM»")
it("no pisa una elección del usuario cuando llega la sugerencia")
it("sin sugerencia (null) queda en Sin convenio")
// AltaIngresoPage: borrador → pide sugerido con paciente_id; alta nueva → con rut válido, no con rut a medio escribir
// EditarFichaDialog: PATCH incluye tipo_convenio; "" viaja como null
```

- [ ] **Step 2: Run** `npx vitest run src/features/convenios/ConvenioSelect.test.tsx src/features/ingresos` → FAIL.
- [ ] **Step 3: Implement** el componente y conectarlo junto al selector de Programa en ambos formularios (en el alta, `sugerencia` = `{paciente_id}` si viene de borrador, si no `{rut}` cuando el RUT escrito valida con la regla de `ingresoSchema`).
- [ ] **Step 4: Run** el mismo comando y `npx tsc --noEmit -p .` → PASS.
- [ ] **Step 5: Commit** `feat(ingresos): selector de convenio precargado desde SALUTEM`

### Task 8: Frontend — selector en el reporte Convenio y ayuda

**Files:**
- Modify: `frontend/src/features/reportes/ReportesPage.tsx:191-245` (`ConvenioTab`)
- Modify: `frontend/src/features/ayuda/contenido.ts` (dónde se administran los convenios y que se crean en SALUTEM)
- Test: el test existente de `ReportesPage` (o uno nuevo `ReportesPage.convenio.test.tsx`)

**Interfaces:**
- Consumes: `useConveniosParaReportes()` (Task 6).

- [ ] **Step 1: Write the failing tests**

```tsx
it("la pestaña Convenio ofrece los convenios del catálogo y los valores antiguos")  // "Convenio SSM", "ISL"
it("generar sin elegir convenio muestra «Indica el tipo de convenio.»")
it("genera con el convenio elegido")                                               // query tipo_convenio exacto
```

- [ ] **Step 2: Run** `npx vitest run src/features/reportes` → FAIL.
- [ ] **Step 3: Implement**: reemplazar el `Input` por un `select` (`id="convenio"`, misma etiqueta «Tipo convenio *») y agregar el texto de ayuda.
- [ ] **Step 4: Run** `npx vitest run` (toda la suite) y `npx tsc --noEmit -p .` → PASS; backend `uv run pytest` → exit 0.
- [ ] **Step 5: Commit** `feat(reportes): el reporte Convenio elige del catálogo`
