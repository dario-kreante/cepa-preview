# Defectos detectados en la revisión del ambiente de pruebas — agosto 2026

**Origen:** `Revisión etapa preliminar SIGE.docx` (María del Pilar García Zerene, CEPA, 27-08-2026).
Transcripción: [`../feedback/2026-08-27-revision-etapa-preliminar-sige.md`](../feedback/2026-08-27-revision-etapa-preliminar-sige.md).
Decisiones derivadas de la misma revisión: [`01-decisiones-v5.md`](./01-decisiones-v5.md).

Estos son **defectos**, no requisitos: comportamientos que el backlog vigente ya exige y que
fallaron al operar el ambiente de pruebas. Los requisitos nuevos de la misma revisión están en
`01-decisiones-v5.md`.

> **Actualización 04-09-2026:** todos los defectos fueron reproducidos (o descartados) en local.
> Ver la sección *Triage* más abajo antes de tomar cualquiera de estos tickets.
>
> **Los pasos de reproducción son una reconstrucción** a partir de las notas de Pilar, que
> registran el síntoma pero no la secuencia exacta ni el dato usado. El primer paso de cada
> ticket es **reproducir el defecto**; si no se reproduce, hay que volver a preguntar antes de
> cerrarlo como "no reproducible".

## Triage: reproducción en local (04-09-2026)

Se levantó el entorno completo en local (FastAPI + Postgres + Vite, datos de `seed_dev_data`) y se
reprodujo cada defecto. **La hipótesis de causa común quedó descartada**: no hay una falla
compartida de persistencia. Lo que hay son cuatro defectos reales de interfaz y dos síntomas que
no se reproducen fuera del ambiente que probó la contraparte.

**Contexto del ambiente que probó Pilar:** `https://cepa-preview.vercel.app`, con backend en
**Render plan `free`** (`render.yaml`: *"el web service free se duerme por inactividad"*). El
propio correo del 02-07-2026 advertía a Pilar de esperas de 30-50 s en la primera carga. Un
backend dormido produce exactamente el síntoma "guardé y no quedó guardado".

| ID | Veredicto | Evidencia |
|----|-----------|-----------|
| BUG-2608-01 | **Reproducido — corregido 15-09-2026** | `PatientSheet.tsx:331` — el botón "Editar ficha" tenía `disabled` hardcodeado, igual que "Nueva licencia" y "Agendar control". **Corrección al triage:** el backend **no** tenía un endpoint para editar el ingreso (solo `/seguimiento`, `/consentimiento` y `/plan`). Se agregó `PUT /api/v1/ingresos/{id}` (todo salvo RUT y folio, auditado) y el diálogo "Editar ficha"; los otros dos botones abren los diálogos de alta de licencia y de control. Verificado en la VM el 15-09 que seguía deshabilitado antes del arreglo. |
| BUG-2608-02 | **Reproducido — dos defectos distintos** | (a) El diálogo "Licencia / RECA" **desborda el viewport** a 1280×720: el título queda cortado sobre el borde superior, y el desplegable "Estado RECA" queda al fondo. (b) El desplegable ofrece un **estado de flujo** (Pendiente/Aprobado/Rechazado/En proceso/No aplica), no la **calificación** que pide la contraparte (EP/EC/AT/AC/NPE/No aplica) — ver v5 D20. |
| BUG-2608-03 | **NO se reproduce en local** | `PATCH /api/v1/controles-medicos/33/licencia` → **200**, toast "Licencia y RECA actualizada", tabla refrescada con los valores nuevos. Apunta al backend dormido de Render, no al código. |
| BUG-2608-04 | **Reproducido — defecto real** | `AltaLicenciaDialog.tsx` presenta **cuatro** campos de fecha en dos pares sin agrupación visual: `Fecha inicio`/`Fecha término` (de la licencia) e `Inicio reposo`/`Fin reposo` (del reposo). Se leen como duplicados. Era la segunda de las dos hipótesis del ticket. |
| BUG-2608-05 | **Reproducido — defecto real** | `ReintegroPage.tsx:352` — "Nuevo caso" es `disabled={!ingresoId}`: hay que buscar y seleccionar un paciente primero, pero **nada lo dice**. Sin `title` ni tooltip, y `disabled:pointer-events-none` impide incluso el hover. Verificado en el DOM: `{disabled: true, title: null}`. |
| BUG-2608-06 | **NO se reproduce en local** | "Editar RECA" abre el diálogo con los valores precargados; `PATCH /api/v1/reintegros/2/reca` → **200**, toast "RECA actualizada". Mismo patrón que BUG-03. |
| BUG-2608-07 | **Reproducido — defecto real** | `AltaLicenciaDialog.tsx:129` — el rótulo es literalmente `Ingreso ID`, un identificador de base de datos expuesto al usuario. |

### Qué hacer con los dos que no se reproducen

`BUG-2608-03` y `BUG-2608-06` **no se corrigen persiguiendo el síntoma**. Lo que se corrige es que
el fallo haya sido **invisible**: la contraparte guardó, no vio ningún error y concluyó que el
sistema no guarda. Las acciones son:

1. Que todo guardado fallido muestre un error explícito y conserve los datos del formulario
   (aplica a los cuatro módulos, no solo a estos dos).
2. Volver a probarlos contra el despliegue nuevo, con el backend despierto, antes de darlos por
   cerrados. **Hasta entonces quedan abiertos**, no cerrados como "no reproducible".

> **Hipótesis de causa común — descartada.** Se sospechó que `-01`, `-03`, `-05` y `-06`
> compartían una falla de persistencia. El triage la descartó: `-01` y `-05` son botones
> deshabilitados en la interfaz (nunca llegan a guardar nada) y `-03` y `-06` guardan
> correctamente en local. Lo único que comparten los cuatro es **haberse visto igual desde
> fuera**: el usuario intenta algo y no pasa nada, sin explicación.

## Resumen

| ID | Módulo | Síntoma | Severidad |
|----|--------|---------|-----------|
| BUG-2608-01 | Ingresos | No fue posible editar la ficha después de crearla | Alta |
| BUG-2608-02 | Controles médicos | El desplegable de RECAS no se abre hacia abajo | Alta |
| BUG-2608-03 | Controles médicos | No se guardaron las actualizaciones manuales | Alta |
| BUG-2608-04 | Licencias médicas | Los ítems de inicio y término de licencia aparecen repetidos | Media |
| BUG-2608-05 | Reintegro | No fue posible cargar un nuevo caso | Alta |
| BUG-2608-06 | Reintegro | No fue posible editar la RECA | Alta |
| BUG-2608-07 | Licencias médicas | El rótulo "ingreso ID" no se entiende | Baja |

---

## [BUG-2608-01] No fue posible editar la ficha de ingreso después de crearla

**Módulo:** Ingresos (`frontend/src/features/ingresos`) · **Severidad:** Alta
**Historia afectada:** `CEPA-010` — Registrar nuevo ingreso en formulario único
**Reportado por:** Pilar García (CEPA), 27-08-2026 — *"No fue posible editar la ficha posteriormente."*

**Pasos de reproducción (reconstruidos)**
1. Iniciar sesión con perfil Administrativo.
2. Crear un ingreso nuevo completando los campos obligatorios y guardar.
3. Abrir el ingreso recién creado desde el listado o desde la búsqueda por RUT/folio.
4. Modificar cualquier campo y guardar.

**Resultado observado:** no se pudo editar la ficha.
**Resultado esperado:** el ingreso es editable por Administrativo y Coordinación; los cambios
persisten y quedan registrados en el log de auditoría (`CEPA-010` DoD).

**Verificación de cierre**
- [ ] El defecto se reprodujo antes de corregirlo (o se documentó por qué no se reprodujo).
- [ ] Un ingreso existente se edita y los cambios persisten tras recargar la página.
- [ ] La edición queda registrada en el log de auditoría con autor y fecha (`CEPA-003`).
- [ ] Perfil Auditor sigue sin poder editar (regresión de RBAC, `TC-010-06`).
- [ ] Test de integración que cubre el ciclo crear → editar → releer.

---

## [BUG-2608-02] El desplegable de RECAS no se abre hacia abajo

**Módulo:** Controles médicos (`frontend/src/features/controles`) · **Severidad:** Alta
**Historia afectada:** `CEPA-062` — Licencias y RECA asociadas al control
**Reportado por:** Pilar García (CEPA), 27-08-2026 — *"No se pudo utilizar el desplegable hacia abajo."*

**Pasos de reproducción (reconstruidos)**
1. Abrir un control médico existente.
2. Hacer clic en el desplegable del apartado RECAS.
3. Intentar seleccionar una opción de la lista.

**Resultado observado:** el desplegable no se despliega hacia abajo / no permite seleccionar.
**Resultado esperado:** el desplegable abre y permite seleccionar cualquier valor del catálogo de
tipo de RECA (D20: EP, EC, AT, AC, NPE, No aplica).

**Notas de diagnóstico**
- Sospechas habituales: `overflow: hidden` en un contenedor padre, `z-index` insuficiente del
  popover, o el desplegable abriendo fuera del viewport al estar cerca del borde inferior.
- Verificar en la resolución que usa el CEPA, no solo en pantalla ancha.
- Pilar indicó *"Incluir foto"*: la captura no venía adjunta en el correo. **Solicitarla** si el
  defecto no se reproduce.

**Verificación de cierre**
- [ ] El desplegable abre y permite seleccionar en el flujo completo del control.
- [ ] Funciona con el desplegable cerca del borde inferior de la ventana (el popover se reubica).
- [ ] Verificado en viewport de 1366×768 además del ancho de escritorio.
- [ ] El valor seleccionado persiste tras guardar y recargar.

---

## [BUG-2608-03] No se guardaron las actualizaciones manuales en controles médicos

**Módulo:** Controles médicos (`frontend/src/features/controles`) · **Severidad:** Alta
**Historia afectada:** `CEPA-060`, `CEPA-062`
**Reportado por:** Pilar García (CEPA), 27-08-2026 — *"No se guardaron las actualizaciones manuales."*

**Pasos de reproducción (reconstruidos)**
1. Abrir un control médico ya registrado.
2. Modificar manualmente uno o más campos (datos de licencia, estado RECA, observaciones).
3. Guardar.
4. Salir de la vista y volver a abrir el control.

**Resultado observado:** los cambios no quedaron guardados.
**Resultado esperado:** los cambios persisten y son visibles al reabrir; si el guardado falla, el
sistema muestra un error explícito y no descarta los datos del formulario.

**Verificación de cierre**
- [ ] Editar y guardar un control persiste tras recargar.
- [ ] Un fallo de guardado (simulado: error 500 del backend) muestra un mensaje de error visible
      y conserva los datos del formulario — **un guardado que falla nunca es silencioso**.
- [ ] Test de integración crear → editar → releer sobre control médico.
- [ ] Revisada la relación con `BUG-2608-01`, `-05` y `-06` (hipótesis de causa común).

---

## [BUG-2608-04] Los ítems de inicio y término de licencia aparecen repetidos

**Módulo:** Licencias médicas (`frontend/src/features/licencias`) · **Severidad:** Media
**Historia afectada:** `CEPA-070` — Registro de licencia médica
**Reportado por:** Pilar García (CEPA), 27-08-2026 — *"Los ítems de inicio y término de licencia están repetidos."*

**Contexto:** `CEPA-070` modela dos pares de fechas que se parecen — `fecha_inicio`/`fecha_termino`
de la licencia (RN-1) e `inicio_reposo`/`fin_reposo` (RN-2, v4 D8). Es probable que el formulario
los presente sin rótulos que los distingan y por eso se lean como duplicados; también es posible
que efectivamente se estén renderizando dos veces.

**Verificación de cierre**
- [ ] Determinado cuál de los dos casos es: duplicación real o rótulos indistinguibles.
- [ ] Si es duplicación: el campo aparece una sola vez.
- [ ] Si son los dos pares de fechas: los rótulos distinguen inequívocamente *fechas de la
      licencia* de *fechas del reposo*, agrupados visualmente por separado.
- [ ] Validado con Pilar que la lectura del formulario ya no es ambigua.

---

## [BUG-2608-05] No fue posible cargar un nuevo caso de reintegro

**Módulo:** Reintegro (`frontend/src/features/reintegro`) · **Severidad:** Alta
**Historia afectada:** `CEPA-040` — Datos del caso de reintegro
**Reportado por:** Pilar García (CEPA), 27-08-2026 — *"No fue posible cargar nuevo caso."*

**Pasos de reproducción (reconstruidos)**
1. Iniciar sesión con perfil Administrativo.
2. Ir a Reintegro → nuevo caso.
3. Completar los campos obligatorios (folio, tipo de derivación, fecha, identificación, región,
   zona geográfica, rubro del empleador) y guardar.

**Resultado observado:** no se pudo cargar el caso.
**Resultado esperado:** el caso de reintegro se crea vinculado al folio y aparece en el listado.

**Notas de diagnóstico**
- Averiguar si el bloqueo fue una validación que rechaza sin explicar (p. ej. folio inexistente en
  el ambiente de pruebas) o un error de guardado. Son correcciones distintas: en el primer caso el
  defecto es **el mensaje**, no la validación.

**Verificación de cierre**
- [ ] Se crea un caso de reintegro nuevo desde la interfaz y aparece en el listado.
- [ ] Cada validación que impide guardar explica **qué campo** y **por qué**.
- [ ] Test de integración de creación de caso de reintegro.
- [ ] Verificado con los pacientes de prueba del CEPA, no solo con datos sembrados.

---

## [BUG-2608-06] No fue posible editar la RECA

**Módulo:** Reintegro (`frontend/src/features/reintegro`) · **Severidad:** Alta
**Historia afectada:** `CEPA-041` — Proceso RECA y medidas correctivas
**Reportado por:** Pilar García (CEPA), 27-08-2026 — *"No fue posible editar la RECA."*

**Pasos de reproducción (reconstruidos)**
1. Abrir un caso de reintegro con RECA registrada.
2. Modificar fecha, tipo o número de RECA, o el ciclo de medidas correctivas.
3. Guardar.

**Resultado observado:** no se pudo editar la RECA.
**Resultado esperado:** la RECA es editable por Administrativo y Coordinación, respetando las
validaciones de coherencia temporal (`CEPA-041` RN-3) y la unicidad del Nº de RECA (RN-1).

**Verificación de cierre**
- [ ] Una RECA existente se edita y los cambios persisten tras recargar.
- [ ] Las validaciones de coherencia temporal siguen activas y explican el rechazo (`TC-041-04`).
- [ ] La unicidad de Nº de RECA no bloquea la edición del propio registro (causa candidata: la
      validación de unicidad no excluye el registro que se está editando).
- [ ] Perfil Auditor sigue sin poder editar (`TC-041-06`).

---

## [BUG-2608-07] El rótulo "ingreso ID" no se entiende

**Módulo:** Licencias médicas (`frontend/src/features/licencias`) · **Severidad:** Baja
**Historia afectada:** `CEPA-070`
**Reportado por:** Pilar García (CEPA), 27-08-2026 — *"¿A qué se refiere con ingreso ID? RUT, folio, nombre."*

Es un defecto de interfaz, no una pregunta de negocio: el usuario no puede saber qué dato se le
está pidiendo. La contraparte incluso sugiere las tres opciones que consideró.

**Verificación de cierre**
- [ ] El campo se renombra a un rótulo explícito en el lenguaje del CEPA (p. ej. "Folio del
      ingreso") y, si admite varios criterios, lo indica en el texto de ayuda.
- [ ] Revisados los demás rótulos del módulo por el mismo problema.
- [ ] Validado con Pilar que el rótulo se entiende sin explicación.
