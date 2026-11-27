# DOCUMENTO DE REGISTRO DE PRUEBAS QA
## SIGE-CEPA — Sistema Interno de Gestión del CEPA

| | |
|---|---|
| Versión del documento | 1.1 (borrador): consolida la ronda del 18 al 23-11-2026 y las correcciones aplicadas el 24-11-2026 |
| Fecha | Noviembre 2026 |
| Ambiente de prueba | QA, `http://segicepa-qa.utalca.cl` |

> Este documento toma el registro de pruebas que elaboró el equipo del CEPA (versión del 18-11-2026, actualizada el 23-11-2026) y agrega, por cada caso, la corrección que aplicó Kreante. **El resultado OK/FAIL lo define el equipo del CEPA** al volver a probar cada caso: la columna «Estado tras re-prueba» queda para que la completen las testers.

---

## 1. Información general

| Dato | Valor |
|---|---|
| Nombre del sistema | Sistema Interno de Gestión SIGE-CEPA |
| Versión | 2026, `main` 878eed8 |
| Módulos en prueba | Dashboard, Reportería, Ingresos y pacientes, Auditoría, ODAS vencidas, Cierre de caso, Controles médicos, Seguimiento EPT, Seguimiento reintegro |
| Responsables QA | María del Pilar García, Alejandra Herrera |
| Fecha de inicio de pruebas | 18-11-2026 |
| Fecha de término de la primera ronda | 23-11-2026 |
| Correcciones disponibles en QA | 24-11-2026 |
| Fecha de re-prueba | **[PENDIENTE: la completa el equipo del CEPA]** |

---

## 2. Alcance de las pruebas

- **Objetivo de la prueba:** validar que SIGE-CEPA cumple los procesos del CEPA y que su integración con SALUTEM es correcta antes del paso a producción.
- **Tipo de prueba:** funcional, de integración (SALUTEM) y de aceptación de usuario (UAT).
- **Metodología QA aplicada:** híbrida. Las testers del CEPA hacen pruebas manuales en el ambiente de QA. Kreante corre pruebas automatizadas en cada cambio (backend y frontend).

### 2.1 Equipo de prueba

María del Pilar García, Alejandra Herrera, Jocelyn Monsalve, Melissa Cabrera, Isidora Figueroa, Valeria, Belén, Carla Mendoza, Carla H., Gissela, Angela y Yasna (YAS).

Los pacientes de prueba creados en SALUTEM QA fueron:
- Bartolomé Simpon
- Bob Esponja Pantalones Cuadrados
- Taylor Swift
- los Minions
- Morita Salchicha
- Karol G
- Paciente de prueba Humberto
- Catherine Neira
- Catalina González
- Brownie Arriagada
- Francisca Valladares
- Lady Gaga

---

## 3. Casos de prueba

### QA-001 — Dashboard

| Campo | Detalle |
|---|---|
| Usuario de prueba | mgarciaz |
| Precondiciones | Atenciones agendadas, atendidas y anuladas en SALUTEM QA |
| Pasos de prueba | Ingresar al sistema, abrir el Dashboard y revisar las tarjetas de actividad del período. |
| Resultado esperado | Las tarjetas se actualizan según SALUTEM: atenciones, anulaciones, agendadas, ingresos, controles médicos y agenda de 7 días. |
| Resultado obtenido (18-11) | Las tarjetas se actualizaron correctamente. |
| Estado ronda 1 | **OK** |
| Fecha / tester | 17-11-2026 · Pilar García |
| Corrección aplicada | No requiere. |
| Estado tras re-prueba | OK |

### QA-002 — Reportería (resumen de atenciones)

| Campo | Detalle |
|---|---|
| Usuario de prueba | mgarciaz |
| Pasos de prueba | Dashboard → tarjeta de atenciones → filtrar las atenciones del mes en curso. |
| Resultado esperado | Resumen de las atenciones de SALUTEM y su estado. |
| Resultado obtenido (18-11) | El resumen aparece. Se sugiere incluir el estado «recepcionado» y dividir las atenciones por programa (Ingreso ISL, Tratamiento ISL, PAPT, Particular, Convenios). |
| Estado ronda 1 | FAIL (sugerencias) |
| Fecha / tester | 17-11-2026 · Pilar García |
| Corrección aplicada | Las citas recepcionadas en SALUTEM aparecen como «recepcionada» y se cuentan en los reportes. Se agregaron los programas «Ingreso ISL» y «Tratamiento ISL». **[PENDIENTE: confirmar si falta la división de atenciones por programa.]** |
| Estado tras re-prueba | **[CEPA]** |

### QA-003 — Ingresos y pacientes (datos desde SALUTEM)

| Campo | Detalle |
|---|---|
| Usuario de prueba | aherrera |
| Precondiciones | Paciente creado en SALUTEM |
| Resultado esperado | La ficha trae desde SALUTEM, de forma concordante, el teléfono, el correo, la comuna y la región. |
| Resultado obtenido (19-11) | La información aparece vacía y la región no coincide (también con la paciente Lady Gaga). |
| Estado ronda 1 | FAIL |
| Fecha / tester | 19-11-2026 · Alejandra Herrera |
| Corrección aplicada | Al completar la ficha ya no se borran la comuna, el teléfono ni el correo; si vienen vacíos, se completan con lo que tenga SALUTEM. Al elegir la comuna, la región se completa sola con la tabla oficial CUT 2018. |
| Estado tras re-prueba | **[CEPA]** |

### QA-004 — Auditoría: reportes y filtros

| Campo | Detalle |
|---|---|
| Usuario de prueba | mgarciaz |
| Pasos de prueba | Auditoría → «Reportes» → elegir fechas y filtros → descargar. |
| Resultado esperado | Se puede filtrar por fecha, estado, diagnóstico y región. |
| Resultado obtenido (19-11) | El filtro no reconoce mayúsculas ni tildes. Se sugieren listas desplegables (estado, región, origen, programa) y quitar el filtro de diagnóstico. |
| Estado ronda 1 | FAIL |
| Fecha / tester | 19-11-2026 · Pilar García |
| Corrección aplicada | Los filtros funcionan con o sin mayúsculas y tildes. Se agregaron los filtros por convenio y por programa, y se quitó el de diagnóstico. Los convenios nuevos se crean en SALUTEM y se traen con «Actualizar desde SALUTEM». |
| Estado tras re-prueba | **[CEPA]** |

### QA-005 — Auditoría: descarga y formato del reporte

| Campo | Detalle |
|---|---|
| Usuario de prueba | JMONSALVE |
| Precondiciones | Casos ingresados (por ejemplo, F-2026-0071 a F-2026-0073) |
| Resultado esperado | Excel (.xlsx) con columnas ordenadas, tildes y ñ correctas, encabezados legibles, filtros activos, fechas dd-mm-aaaa, campos Sí/No, y RUT y folio como texto. |
| Resultado obtenido (20-11) | El CSV abre todo en la columna A, con caracteres extraños («PiolÃn»), encabezados con guiones bajos y True/False. |
| Estado ronda 1 | FAIL |
| Fecha / tester | 20-11-2026 · Jocelyn Monsalve |
| Corrección aplicada | La descarga ahora es un Excel con columnas claras. |
| Estado tras re-prueba | **[CEPA]** |

### QA-006 — Reportería: ODAS vencidas

| Campo | Detalle |
|---|---|
| Usuario de prueba | ADMCEPA |
| Pasos de prueba | Reportería → «ODAS vencidas» → descargar Excel. |
| Resultado esperado | Se descarga el reporte de ODAS vencidas. |
| Resultado obtenido (23-11) | Se solicitan cambios: una fila por fecha de atención; columnas de programa, región, ciudad y folio; renombrar «N° ODA y OPA»; identificar el tipo (ODA/OPA). |
| Estado ronda 1 | FAIL |
| Fecha / tester | 23-11-2026 · Melissa Cabrera |
| Corrección aplicada | El Excel trae una fila por atención, con las columnas folio, programa, región y comuna. **[PENDIENTE: nombre definitivo de la columna «N° ODA/OPA» («N° de siniestro» o «N° de atención»); se preguntó al CEPA el 24-11.]** |
| Estado tras re-prueba | **[CEPA]** |

### QA-007 — Cierre y reapertura del caso

| Campo | Detalle |
|---|---|
| Usuario de prueba | mgarcia |
| Pasos de prueba | Ingresos y pacientes → ficha → cerrar el caso con motivo → verificar → reabrir. |
| Resultado esperado | Queda registrado el motivo y la fecha de cierre. Al reabrir, se conserva el registro del cierre anterior. |
| Resultado obtenido (23-11) | El cierre funciona, pero al reabrir avisa que se borrará el motivo y la fecha del cierre anterior. |
| Estado ronda 1 | FAIL |
| Fecha / tester | 23-11-2026 · Pilar García |
| Corrección aplicada | Se cierra un solo caso a la vez. Al reabrir, el historial de cierres anteriores se conserva y se ve en la ficha. El botón «Cerrar caso» quedó junto a las demás acciones de la ficha. |
| Estado tras re-prueba | **[CEPA]** |

### QA-008 — Controles médicos: addendum de SALUTEM

| Campo | Detalle |
|---|---|
| Usuario de prueba | aherrera |
| Precondiciones | Addendum agregado en SALUTEM al control médico AT del 27-10 del paciente de prueba Humberto |
| Resultado esperado | SIGE indica que el control tiene addendum. |
| Resultado obtenido (23-11) | No lo indica, o lo muestra en un control equivocado (26-10) y con el texto cortado. |
| Estado ronda 1 | FAIL |
| Fecha / tester | 23-11-2026 · Alejandra Herrera |
| Corrección aplicada | Las notas que el profesional escribe en SALUTEM aparecen en el control médico de SIGE. Si una nota contiene «addendum» (también «adendum» o «adenda»), se marca con una etiqueta. **[PENDIENTE: que el CEPA confirme que el equipo escribirá siempre esa palabra.]** |
| Estado tras re-prueba | **[CEPA]** |

### QA-009 — Seguimiento EPT

| Campo | Detalle |
|---|---|
| Usuario de prueba | mgarciaz |
| Pasos de prueba | Seguimiento EPT → buscar a Brownie Arriagada → crear EPT → completar los campos. |
| Resultado esperado | Se crea el caso y se generan de inmediato las alertas de insumos, informe EPT e informe ISL, según los plazos del convenio. |
| Resultado obtenido (23-11) | Se crea el caso, pero no se ven alertas. Se sugiere buscar por folio, nombre o RUT, precargar los datos del paciente y ajustar la regla de plazos. |
| Estado ronda 1 | FAIL |
| Fecha / tester | 23-11-2026 · Pilar García |
| Corrección aplicada | Una sola EPT por ingreso, con búsqueda por folio, nombre o RUT y el formulario precargado. El informe vence a los 15 días del ingreso y el portal ISL a los 19; si cae en fin de semana o feriado, se adelanta al día hábil anterior. Las alertas aparecen apenas se guarda la EPT. |
| Estado tras re-prueba | **[CEPA]** |

### QA-010 — Seguimiento reintegro

| Campo | Detalle |
|---|---|
| Usuario de prueba | ifigueroa |
| Precondiciones | Atención con reintegro parcial y proyección de reintegro total en 2 semanas (paciente Catherine Neira) |
| Resultado esperado | La alerta lleva al caso de reintegro. Hay seguimiento de las proyecciones y de los reintegros parciales, un listado de casos activos, datos traspasados automáticamente y alertas de pendientes de remitir a ISL. |
| Resultado obtenido (23-11) | La alerta lleva a registrar la licencia médica, no al reintegro. No hay lista de pendientes ni traspaso automático de datos. Sin «Remitido a ISL» no hay alerta. |
| Estado ronda 1 | FAIL |
| Fecha / tester | 23-11-2026 · Isidora Figueroa |
| Corrección aplicada | Alertas según la proyección de reintegro («reintegro parcial» y «1, 2 o 3 semanas aproximadamente»). Listado con todos los reintegros. Nuevos campos «ocupación» y «fecha de remisión a ISL». Alerta «Pendiente de remitir a ISL» a los 7 días, excepto en casos de más de 60 días. RECA: 15 días corridos desde el envío de la EPT, solo para pacientes ISL. |
| Estado tras re-prueba | **[CEPA]** |

### CA-012 — Auditoría: perfil mixto

| Campo | Detalle |
|---|---|
| Usuario de prueba | ifigueroa |
| Resultado esperado | Un perfil mixto (administrativo y auditor) para quien hace reintegro y auditoría clínica. |
| Resultado obtenido (23-11) | Sin permisos para entrar a Auditoría. |
| Estado ronda 1 | FAIL |
| Fecha / tester | 23-11-2026 · Isidora Figueroa |
| Corrección aplicada | Ver Auditoría es ahora un permiso que se asigna a cada usuario («Acceso a Auditoría»). Un administrativo con ese permiso mantiene sus funciones y además entra a Auditoría. **[PENDIENTE: que el CEPA indique a qué personas asignarlo.]** |
| Estado tras re-prueba | **[CEPA]** |

---

## 4. Registro de incidencias

| ID | Descripción | Severidad | Estado | Fecha reporte | Responsable corrección |
|---|---|---|---|---|---|
| QA-002 | Estado «recepcionado» y división por programa en el resumen de atenciones | Baja | Corregida parcialmente, en re-prueba | 17-11-2026 | Darío Ramírez |
| QA-003 | Datos de contacto y región no concuerdan con SALUTEM | Alta | Resuelta, en re-prueba | 19-11-2026 | Darío Ramírez |
| QA-004 | Filtros de Auditoría sensibles a mayúsculas y tildes | Media | Resuelta, en re-prueba | 19-11-2026 | Darío Ramírez |
| QA-005 | Formato del reporte de Auditoría | Media | Resuelta, en re-prueba | 20-11-2026 | Darío Ramírez |
| QA-006 | Columnas y detalle del reporte de ODAS vencidas | Media | Resuelta, falta definir el nombre de una columna | 23-11-2026 | Darío Ramírez |
| QA-007 | Se pierde el historial al reabrir un caso | Media | Resuelta, en re-prueba | 23-11-2026 | Darío Ramírez |
| QA-008 | Addendum de SALUTEM no visible en el control | Media | Resuelta, depende de la convención de escritura | 23-11-2026 | Darío Ramírez |
| QA-009 | Alertas EPT no visibles y regla de plazos | Alta | Resuelta, en re-prueba | 23-11-2026 | Darío Ramírez |
| QA-010 | Flujo de alertas y seguimiento de reintegro | Alta | Resuelta, en re-prueba | 23-11-2026 | Darío Ramírez |
| CA-012 | Acceso a Auditoría para perfil administrativo | Media | Resuelta, falta la asignación de permisos | 23-11-2026 | Darío Ramírez |

**Severidad:** Alta = no se puede continuar o afecta una tarea importante; Media = se puede continuar con dificultad; Baja = molestia menor.

### 4.1 Puntos que solo se pueden validar en producción

- **Conteo de sesiones** (alerta de ampliación): SALUTEM QA no tiene registradas las primeras consultas psicológicas ni psiquiátricas. Se valida con datos reales en producción.
- **Correo de alertas:** hoy las alertas se muestran en pantalla. El envío por correo requiere que DTI habilite una cuenta y un relay SMTP para los servidores del SIGE (solicitud enviada al CEPA el 24-11-2026).

---

## 5. Resumen de resultados

| Indicador | Ronda 1 (18 al 23-11-2026) | Re-prueba |
|---|---|---|
| Casos totales ejecutados | 11 | **[CEPA]** |
| Casos exitosos (OK) | 1 | **[CEPA]** |
| Casos fallidos (FAIL) | 10 | **[CEPA]** |
| Porcentaje de éxito | 9 % | **[CEPA]** |

**Observaciones:** las 10 incidencias de la ronda 1 tienen una corrección disponible en QA desde el 24-11-2026. Tres de ellas quedan sujetas a una definición del CEPA: el nombre de la columna en QA-006, la convención del addendum en QA-008 y la asignación del permiso de Auditoría en CA-012. QA-002 está corregida solo en parte.

---

## 6. Evidencias gráficas

Las capturas de la ronda 1 están en el documento del equipo del CEPA, «Documento_Registro_Pruebas_QA_SIGE_CEPA_18-11-2026», sección 6. Las evidencias de la re-prueba se agregan en esta sección:

**[CEPA: capturas de la re-prueba por caso]**

---

## 7. Aprobaciones

| Rol | Nombre | Firma / fecha |
|---|---|---|
| Tester responsable | María del Pilar García, Alejandra Herrera | |
| Líder QA | María del Pilar García | |
| Proveedor (Kreante) | Darío Ramírez | |
| Cliente / usuario final | Equipo del CEPA (funcionarios, profesionales, técnicos y administrativos) | |
