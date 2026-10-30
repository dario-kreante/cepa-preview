# Reunión revisión SIGE-CEPA — 29-10-2026 15:00

Estado de los pedidos de los informes de QA del 22-10 y 23-10 (Pilar García, Alejandra Herrera).

## Ya en dev y QA (PR #60, 23-10)

| Caso | Qué cambió |
|---|---|
| 22-10 QA-003 | EPT: buscar los casos por paciente («Abrir») y borrar un caso creado por error |
| 22-10 QA-004 | Auditoría: un solo buscador libre (nombre, RUT, folio, N° de siniestro) |
| 22-10 QA-005 | Tipo de derivación «Reingreso ISL» |
| 22-10 QA-007 | Campo «Comentarios» en Nuevo control |
| 22-10 QA-008 | Reintegro: el alta no exige RUT y se precarga con los datos del paciente |
| 23-10 QA-002 / QA-005 | Licencias y fármacos toman el ingreso más reciente del paciente |
| 23-10 QA-003 | Registros de SALUTEM ordenados del más reciente al más antiguo |
| 23-10 QA-005 | Fármacos: recetas por fecha, esquema vigente primero, columna «Desde» |

## Nuevo, listo para probar (rama `claude/qa-pilar-alcance-nuevo`)

| Caso | Qué cambió |
|---|---|
| 22-10 QA-002 | Controles muestra todas las prestaciones médicas de SALUTEM: Médico/a y Médico/a AT; Primera consulta médica AT y EP; Psiquiatría; Evaluación médica (general, AT, EP y PIPT); Evaluación psiquiátrica; Consultoría psiquiátrica. Columna nueva «Prestación». |
| 22-10 QA-001 | Los documentos de SALUTEM salen del control desplegado. Licencias muestra «Documentos de licencias en SALUTEM», Fármacos muestra «Recetas en SALUTEM» y Controles muestra la biblioteca completa a nivel paciente. |
| 22-10 QA-003 | EPT con los 24 factores de riesgo del listado del área. Los casos antiguos se ven como «(anterior) …» y al editarlos se pide un factor nuevo. |
| 22-10 QA-004 | «Cargar reporte ISL» en Reportería → ODAS: sube el Excel «Reporte Prestador», previsualiza, carga las ODA/OPA por N° de siniestro y alerta el vencimiento solo de pacientes activos. Si se sube dos veces, no se duplica nada. |
| 22-10 QA-006 | Nueva licencia: sin las fechas de reposo duplicadas; el reposo toma las fechas de la licencia. |
| 22-10 QA-008 | Alta de reintegro sin edad ni sexo, con «Razón social de la empresa» (precargada) y «Tipo de trabajador» (dependiente / independiente). |

## Revisión en QA (29-10, 11:00, usuario Administrativo)

| Pantalla | Resultado |
|---|---|
| Controles (Humberto) | ✅ 6 controles con «Prestación»; aparece la Primera consulta médica AT del 20-10. El control desplegado ya no muestra documentos; la biblioteca queda a nivel paciente. ⚠️ Los 5 documentos salen marcados «Licencia», incluidas las circulares EPT: la deducción por fecha no alcanza. ⚠️ La tabla va de más antiguo a más reciente. |
| Licencias (Humberto) | ✅ «Nueva licencia» sin fechas de reposo; sección «Documentos de licencias en SALUTEM». ⚠️ Sigue «Sin licencias para este paciente»: la licencia de SALUTEM solo existe como alerta («licencia en control») y entra al módulo recién cuando se gestiona desde la alerta. |
| Fármacos (Humberto) | ✅ Sección «Recetas en SALUTEM» (vacía: ninguna atención indicó receta). ⚠️ Mismo vacío que Licencias: lo de SALUTEM no aparece en el módulo por sí solo. |
| EPT | ✅ Selector con los 24 factores, sin valor preseleccionado. Los casos antiguos de Sasha están en dev, no en QA. |
| Reintegro (Humberto) | ✅ Alta sin edad ni sexo, con razón social y tipo de trabajador. La razón social sale vacía porque el ingreso no la tiene. |
| Reportería → ODAS | ✅ Vista previa con la planilla de prueba: 2.633 filas leídas, 0 errores, nada guardado. ⚠️ 0 coincidencias: los pacientes de prueba no tienen N° de siniestro y la columna «Rut Trabajador» viene vacía. |

## Para conversar

1. **Documentos por carpeta (QA-001).** SALUTEM no informa en qué carpeta está cada archivo (licencias, recetas, OPA/ODA). Hoy el sistema deduce la relación por la atención del día en que se subió el archivo. Para separarlos de verdad, SALUTEM tiene que entregar la carpeta en su API. ¿Lo pedimos?
2. **Alerta de alta próxima (QA-007 / QA-008).** SALUTEM entrega «Proyección de reintegro laboral» como texto libre, y en algunas fichas «Número de sesión actual / Número de sesiones por tratamiento». ¿Qué dato debe disparar la alerta y con cuánta anticipación? Con esa definición se construye la alerta que abre el caso de reintegro.
3. **Reporte ISL (QA-004).** En la planilla de prueba la columna «Rut Trabajador» viene vacía, así que el cruce se hace solo por N° de siniestro. Las órdenes cuyo siniestro no está en SIGE aparecen en el resumen como «sin paciente». ¿Las planillas reales traen el RUT del trabajador?
4. **Pruebas con fichas reales (correo del 22-10).** El ambiente QA de SALUTEM no tiene las fichas actualizadas. Propuesta: validar las prestaciones del Excel en el paso a producción, con un grupo acotado de pacientes.
5. **Dashboard sin actualizar (23-10 QA-004).** Desde el 23-10 a las 09:20, SALUTEM QA responde `SIN_INTEGRACION_CONFIGURADA` a la integración de la empresa 96. Es un problema del lado de SALUTEM: hay que pedirles que la restablezcan.
6. **Licencias y recetas de SALUTEM en sus módulos.** Hoy solo llegan como alertas, y hay que gestionarlas para que aparezcan en Licencias o Fármacos. Propuesta: mostrar en cada módulo una sección «Informadas en SALUTEM, pendientes de registrar», con el botón para registrarlas.
7. **N° de siniestro en los pacientes de prueba.** Para probar la carga del reporte ISL se necesita al menos un paciente con un N° de siniestro que esté en la planilla.
8. **Dónde prueban.** Las testers usan la VM de **dev**. Confirmar que siguen ahí.

---

## Acta (29-10, 15:02–16:18)

Transcripción completa: [2026-10-29-reunion-revision-sige-transcripcion.md](2026-10-29-reunion-revision-sige-transcripcion.md).

Asistentes: Pilar García, Alejandra Herrera, Melissa Cabrera, Jocelyn, Gissela, Paula Sánchez, Sasha Cofré,
Carla Hevia, Gustavo Espinoza y Darío Ramírez. Darío presentó la arquitectura (sync SALUTEM de solo lectura
en 3 ritmos), los perfiles y los módulos. El equipo planteó dudas y pedidos por módulo.

### Plazos

- Un par de semanas más de pruebas, hasta no tener observaciones. Después vienen la revisión de los
  comités y la de la DTI.
- Paso a producción hacia **fines de diciembre 2026**. Desde los ingresos de **enero 2027** se usa SIGE
  al 100 %, con un par de meses de corrección en operación.
- Próxima actualización comprometida: **viernes 30-10 por la tarde**, con el rol superadministrador y
  algunos de los ajustes. Hay que avisarle a Pilar cuando esté.
- El contrato del CEPA con SALUTEM llega hasta 2028.

### Tareas de Darío (desarrollo)

| # | Tarea | Pedido por | Notas |
|---|---|---|---|
| D1 | ✅ Mandar a Pilar por WhatsApp la captura del error de SALUTEM y desde cuándo ocurre | Pilar / SALUTEM | Enviado el 29-10. `SIN_INTEGRACION_CONFIGURADA` desde el 23-10 09:20, empresa 96, qa.salutem.cl. |
| D2 | ✅ Rol nuevo **superadministrador** (todo: EPT, corregir folio, auditoría, etc.) para Pilar y Alejandra | Pilar | Desplegado el 29-10 16:39 en dev y QA; dramirezr, aherrera y mgarcia ya son Superadmin. |
| D3 | ✅ Revisar por qué Pilar no pudo cambiar el folio | Pilar | Era el permiso (lo resuelve D2) y el alta no tenía campo «Folio»: se agregó (opcional; vacío = automático). Antes: corregir folio es solo para Administrativo. Ella necesita editarlo al completar el registro (folios internos por programa). |
| D4 | ✅ Control médico: dejar editar a mano días/reposo (y datos de licencia) cuando SALUTEM no los trae o un adendum los corrige | Pilar | «Licencia/RECA» y «Evaluación» ya editaban, pero el sync volvía a escribir la ficha. Ahora el control guarda los campos corregidos (migración 1390) y el sync no los pisa; la tabla los marca «Corregido». |
| D5 | ✅ Estado de paciente **«En encuadre»** (manual, junto a activo/cerrado) | Jocelyn, Pilar, Gissela | |
| D6 | ✅ Alerta de **inasistencias para encuadre**: desde la 2.ª inasistencia, contando el histórico; cada inasistencia nueva vuelve a alertar | Jocelyn, Pilar, Gissela | Se acordó alertar todas y que el equipo revise si el paciente está en tratamiento o en acompañamiento. |
| D7 | Alertas por correo: activarlas con la lista de correos institucionales, destinatarios por tipo de alerta (p. ej. recetas → prestaciones médicas) y opción de desactivarlas en la configuración personal | Pilar | Darío revisa si se configura por tipo. Depende de P2. |
| D8 | Alerta de **anulación de cita**, la haga quien la haga (paciente por correo o WhatsApp, administrativo o profesional) | Pilar, Paula | Buscar un caso en el historial. Depende de que SALUTEM vuelva y de P6. |
| D9 | ✅ ODA: alerta cuando un control o atención cae **fuera de la vigencia de la ODA** (fecha de atención vs. inicio/término) | Jocelyn, Melissa | La carga del Excel del ISL y el aviso de vencimiento ya están en PR #61. Responder en el grupo que eso ya existe. El cruce por fecha de atención es nuevo. |
| D10 | ✅ EPT: **plazo de insumos** (documentos del empleador → EPTista) con alerta el mismo día del plazo, para todos los casos | Sasha | El plazo ya existía como «Plazo insumos empresa» en Proceso EPT; se agregó la alerta del mismo día (migración 1420, configurable). |
| D11 | EPT: selección múltiple de **hasta 3 factores de riesgo** | Carla | Hoy hay uno solo de los 24 subfactores (PR #61). |
| D12 | ✅ EPT: revisar con Sasha que ya encuentra los casos por nombre/RUT/ID y que puede borrar los creados por error | Sasha | Sus casos 21–23 se crearon en **dev** el 21-10, antes del PR #60. Verificado en QA el 29-10: buscar paciente → lista de casos → «Abrir» → «Eliminar». La etiqueta «EISTA» pasa a «EPTista». Pedirle que lo pruebe en QA. |
| D13 | Probar el botón masivo «marcar como enviadas» de Licencias | Darío | |
| D14 | Revisar que todas las tarjetas del dashboard sean clicables y lleven al lugar correcto | Darío | |
| D15 | Futuro (no ahora): leer un campo sí/no de «receta» en la ficha de SALUTEM e integrar los adendum | Pilar | Solo se puede probar en producción. Queda para una versión posterior. |

### Tareas del CEPA

| # | Tarea | Responsable |
|---|---|---|
| P1 | Pedir a la DTI que SIGE sea accesible desde fuera de la red UTalca (teletrabajo); si no, VPN para quien la necesite | Pilar |
| P2 | Enviar la lista de correos institucionales para las alertas por mail | Pilar |
| P3 | Enviar la lista de campos a agregar/quitar en «Completar registro» del folio pendiente (p. ej. tipo de programa) | Pilar |
| P4 | Preguntar a SALUTEM si su API puede informar la carpeta del documento (licencias / recetas / ODA) | Pilar |
| P5 | Gestionar con SALUTEM la caída de la integración (con la captura de D1) | Pilar |
| P6 | Cuando vuelva la integración: crear un paciente nuevo y una cita, y anularla por los distintos medios, para probar folio pendiente y anulaciones | Pilar |
| P7 | Registrar todas las observaciones de las pruebas en el documento de incidencias | Todo el equipo |
