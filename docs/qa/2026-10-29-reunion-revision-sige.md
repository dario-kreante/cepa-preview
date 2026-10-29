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
