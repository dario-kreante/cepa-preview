# Matriz de Trazabilidad de Requisitos (RTM) — Sistema CEPA

> Generada el 2026-07-02. Mapea cada Test Case a su historia (CEPA-XXX) y fuente (CA = criterio de aceptación Gherkin, BR/RN = regla de negocio, TC = test case legado del backlog, PLANILLA = hoja del Anexo 4).

| US ID | Fuente | Source ID | Descripción de la fuente | TC ID | Reglas de negocio |
|---|---|---|---|---|---|
| CEPA-001 | AC | CA-1 | Dado usuario activo en login, cuando ingresa credenciales válidas, entonces se emite JWT firmado sobre SSL/TLS y se redirige al panel de su rol | TC-CEPA-001-001 | RN-1, RN-2 |
| CEPA-001 | AC | CA-2 | Dado JWT expirado con refresh vigente, cuando el usuario opera, entonces la sesión se renueva sin pedir credenciales | TC-CEPA-001-002 | RN-1 |
| CEPA-001 | AC | CA-3 | Dado credenciales incorrectas reiteradas, cuando alcanza N intentos fallidos, entonces la cuenta se bloquea temporalmente y se registra en auditoría | TC-CEPA-001-003 | RN-3, RN-5 |
| CEPA-001 | AC | CA-4 | Dado cliente sin cifrado o con token inválido/expirado, cuando envía la petición, entonces se rechaza con HTTP no autorizado sin exponer datos | TC-CEPA-001-004 | RN-2 |
| CEPA-001 | BR | RN-3 | Tras N intentos fallidos la cuenta se bloquea temporalmente; el desbloqueo es por tiempo o por intervención de Coordinación | TC-CEPA-001-005 | RN-3 |
| CEPA-001 | BR | RN-4 | Los datos sensibles de salud mental nunca se incluyen en el payload del JWT; solo identidad de usuario y rol | TC-CEPA-001-006 | RN-4 |
| CEPA-001 | BR | RN-5 | Todo intento de inicio de sesión (éxito, fallo, bloqueo) genera traza en el log de auditoría | TC-CEPA-001-007 | RN-5, RN-3 |
| CEPA-001 | TC | TC-001-03 | Negativo: contraseña incorrecta rechazada con mensaje genérico sin revelar el campo fallido | TC-CEPA-001-008 |  |
| CEPA-002 | AC | CA-1 | Dado Coordinación en gestión de usuarios, cuando crea un usuario con uno de los 3 perfiles, entonces queda habilitado con esos permisos y visible en el listado | TC-CEPA-002-001 | RN-1, RN-4 |
| CEPA-002 | AC | CA-2 | Dado los 3 perfiles operativos, cuando Coordinación revisa los perfiles disponibles, entonces el sistema no ofrece el perfil Clínico (v4 D1) | TC-CEPA-002-002 | RN-1 |
| CEPA-002 | AC | CA-3 | Dado un Auditor con sesión, cuando abre un módulo con datos clínicos, entonces solo lectura y edición bloqueada | TC-CEPA-002-003 | RN-2, RN-3 |
| CEPA-002 | AC | CA-4 | Dado un Administrativo, cuando solicita crear o editar un usuario, entonces el sistema deniega por falta de permisos | TC-CEPA-002-004 | RN-4, RN-5 |
| CEPA-002 | AC | CA-5 | Dado un usuario que deja el CEPA, cuando Coordinación lo desactiva, entonces pierde el acceso de inmediato y el cambio queda en auditoría | TC-CEPA-002-005 | RN-4, RN-7 |
| CEPA-002 | BR | RN-2 | Permisos diferenciados por módulo: edición (CRUD) vs. solo lectura según la función del usuario | TC-CEPA-002-006 | RN-2, RN-5 |
| CEPA-002 | BR | RN-3 | El Auditor tiene lectura total y acceso al módulo de Auditoría y reportes de cumplimiento, sin edición de datos clínicos | TC-CEPA-002-007 | RN-3, RN-2 |
| CEPA-002 | BR | RN-6 | La cantidad de usuarios por perfil queda abierta; no hay límite fijo de cupos por perfil | TC-CEPA-002-008 | RN-6 |
| CEPA-002 | BR | RN-7 | Toda alta, baja o cambio de rol de un usuario se registra en el log de auditoría | TC-CEPA-002-009 | RN-7 |
| CEPA-003 | AC | CA-1 | Dado una operación CRUD sobre cualquier registro, cuando se confirma, entonces se registra traza con usuario, operación, registro y fecha/hora | TC-CEPA-003-001 | RN-1, RN-2 |
| CEPA-003 | AC | CA-2 | Dado una traza existente, cuando cualquier usuario intenta modificarla o eliminarla, entonces el sistema lo impide: log inmutable | TC-CEPA-003-002 | RN-3 |
| CEPA-003 | AC | CA-3 | Dado acceso al log, cuando Auditor/Coordinación aplica filtros por usuario, módulo, operación y fechas, entonces se muestran las trazas que cumplen los criterios | TC-CEPA-003-003 | RN-4, RN-5 |
| CEPA-003 | AC | CA-4 | Dado un Administrativo, cuando solicita la vista del log de auditoría, entonces el sistema deniega el acceso por falta de permisos | TC-CEPA-003-004 | RN-5 |
| CEPA-003 | BR | RN-2 | Cada traza registra mínimo: usuario, perfil/rol, operación, entidad y registro, valor anterior/nuevo cuando aplica, y marca temporal | TC-CEPA-003-005 | RN-2, RN-1 |
| CEPA-003 | BR | RN-5 | El acceso de lectura al log se restringe a Auditor y Coordinación; ningún otro perfil puede visualizarlo | TC-CEPA-003-006 | RN-5, RN-3 |
| CEPA-003 | TC | TC-003-05 | Negativo: operación CRUD falla a mitad de transacción; no queda traza parcial inconsistente | TC-CEPA-003-007 | RN-1 |
| CEPA-010 | AC | CA-1 | Dado un RUT válido que ya existe, cuando se ingresa, el sistema pre-llena los datos y permite confirmar o actualizar | TC-CEPA-010-001 | RN-3 |
| CEPA-010 | AC | CA-2 | Dado un formulario con todos los obligatorios, cuando guarda, se genera folio único automático y el registro aparece en búsquedas | TC-CEPA-010-002 | RN-2, RN-4 |
| CEPA-010 | AC | CA-3 | Dado un ingreso con RUT inválido, cuando hace clic en guardar, se muestra error específico sin perder los datos ya ingresados | TC-CEPA-010-003 | RN-1, RN-5 |
| CEPA-010 | AC | CA-4 | Dado un formulario incompleto, cuando intenta guardar sin campos obligatorios, el sistema bloquea el guardado y resalta los faltantes | TC-CEPA-010-004 | RN-2 |
| CEPA-010 | AC | CA-5 | Dado el desplegable de tipo de derivación, cuando se revisan las opciones, solo aparecen los 9 valores válidos v4 D4 | TC-CEPA-010-005 | RN-6 |
| CEPA-010 | BR | RN-6 | Solo son válidos los 9 tipos de derivación v4 D4; el antiguo 'convenio SOCORRO' ya no es válido | TC-CEPA-010-006 | RN-6 |
| CEPA-010 | BR | RN-7 | Campos del formulario §7.1.1: folio, mes y fecha de ingreso, fecha DIEP/DIAT, datos del paciente, tipo de derivación, razón social | TC-CEPA-010-007 | RN-7 |
| CEPA-010 | TC | TC-010-06 | Usuario perfil Auditor intenta abrir/guardar formulario de nuevo ingreso; acceso denegado | TC-CEPA-010-008 |  |
| CEPA-010 | PLANILLA | Ingresos | Hoja 'Ingresos' del Excel CEPA: 846+ registros, 27 columnas (A1:AA846) | TC-CEPA-010-009 | RN-7 |
| CEPA-010 | PLANILLA | Ingresos | Columnas tipo lista de la hoja 'Ingresos' (SI/NO, estados, tipos de alta) deben ser catálogos cerrados | TC-CEPA-010-010 | RN-6 |
| CEPA-010 | PLANILLA | Ingresos | La planilla histórica contiene celdas vacías y valores 'S/D' en columnas no obligatorias | TC-CEPA-010-011 | RN-2 |
| CEPA-011 | AC | CA-1 | Dado un ingreso nuevo sin folio, cuando guarda, el sistema asigna un folio secuencial automático único | TC-CEPA-011-001 | RN-1 |
| CEPA-011 | AC | CA-2 | Dado un reingreso tras alta, cuando se usa folio manual con el folio anterior, el sistema lo acepta y vincula el reingreso | TC-CEPA-011-002 | RN-2, RN-3 |
| CEPA-011 | AC | CA-3 | Dado un ingreso recibido después de las 15:00 lun-jue, cuando se registra, se permite asignar la fecha del día hábil siguiente | TC-CEPA-011-003 | RN-2 |
| CEPA-011 | AC | CA-4 | Dado un mismo RUT con DIAT 2020 y DIEP 2026, cuando se registra el segundo caso, se diferencia reingreso de nueva denuncia por número de siniestro | TC-CEPA-011-004 | RN-4 |
| CEPA-011 | BR | RN-2 | Opción de folio manual para tres casos v4 D2: reingresos, folios pre-asignados del Excel, e ingresos posteriores a las 15:00 | TC-CEPA-011-005 | RN-2 |
| CEPA-011 | BR | RN-3 | Un folio manual no puede colisionar con un folio ya emitido salvo reingreso explícito del mismo paciente | TC-CEPA-011-006 | RN-1, RN-3 |
| CEPA-011 | BR | RN-5 | El contador secuencial automático debe continuar sin saltos no controlados tras un ingreso manual | TC-CEPA-011-007 | RN-1, RN-5 |
| CEPA-011 | TC | TC-011-06 | Usuario perfil Auditor intenta editar folio manualmente; acceso denegado | TC-CEPA-011-008 |  |
| CEPA-012 | AC | CA-1 | Dado un RUT, nombre o folio existente, cuando se busca, se muestra el paciente con todas sus dimensiones en una sola pantalla | TC-CEPA-012-001 | RN-1, RN-3 |
| CEPA-012 | AC | CA-2 | Dado el estado completo de un caso, cuando se ejecuta la búsqueda, se presenta el consolidado en menos de 10 segundos (OU3) | TC-CEPA-012-002 | RN-2 |
| CEPA-012 | AC | CA-3 | Dado un término sin coincidencias, cuando se busca, el sistema informa que no hay resultados sin error | TC-CEPA-012-003 | RN-5 |
| CEPA-012 | AC | CA-4 | Dado un nombre parcial con coincidencias múltiples, cuando se busca, se listan los pacientes coincidentes para seleccionar | TC-CEPA-012-004 | RN-1 |
| CEPA-012 | BR | RN-4 | El acceso a la vista 360° respeta RBAC; el perfil Auditor accede en solo lectura | TC-CEPA-012-005 | RN-4 |
| CEPA-013 | AC | CA-1 | Dado un ingreso, cuando se registra primera acogida y estado de consentimiento, el sistema guarda fecha y estado en el caso | TC-CEPA-013-001 | RN-1 |
| CEPA-013 | AC | CA-2 | Dado un ingreso en evaluación, cuando se registran evaluación médica y psicológica, el sistema actualiza el avance del proceso | TC-CEPA-013-002 | RN-1, RN-2 |
| CEPA-013 | AC | CA-3 | Dado un plazo de informe por programa, cuando la evaluación no se realiza dentro del plazo, el validador indica incumplimiento (v4 D10) | TC-CEPA-013-003 | RN-3 |
| CEPA-013 | AC | CA-4 | Dado un ingreso en proceso, cuando se registran obstaculización, plazos de informe y RECA EP/EC, el sistema los almacena y muestra | TC-CEPA-013-004 | RN-1 |
| CEPA-013 | BR | RN-2 | Estados de evaluación válidos: realizada / pendiente / no aplica | TC-CEPA-013-005 | RN-2 |
| CEPA-013 | BR | RN-3 | El validador de plazos por programa calcula si la evaluación se realizó dentro del plazo y expone un estado de cumplimiento (v4 D10) | TC-CEPA-013-006 | RN-3 |
| CEPA-013 | BR | RN-4 | El registro de cada hito queda con trazabilidad (quién y cuándo) en el log de auditoría | TC-CEPA-013-007 | RN-4 |
| CEPA-013 | BR | RN-5 | El perfil Auditor visualiza el seguimiento en solo lectura | TC-CEPA-013-008 | RN-5 |
| CEPA-014 | AC | CA-1 | Dado un caso activo, cuando se cambia el estado a cerrado o derivado, el sistema lo actualiza y lo refleja en la vista del paciente | TC-CEPA-014-001 | RN-1, RN-5 |
| CEPA-014 | AC | CA-2 | Dado un cierre de caso, cuando se registra el tipo de alta del catálogo, el sistema guarda el tipo y la fecha asociada | TC-CEPA-014-002 | RN-2 |
| CEPA-014 | AC | CA-3 | Dado un caso con seguimiento especial, cuando se activa el flag de revisión y se agregan observaciones, el sistema los persiste | TC-CEPA-014-003 | RN-3 |
| CEPA-014 | AC | CA-4 | Dado que se opta por fecha de alta única (v4 D11), cuando se cierra el caso, se registra la fecha de la última atención como fecha de alta | TC-CEPA-014-004 | RN-4 |
| CEPA-014 | BR | RN-2 | Tipos de alta válidos (§7.1.3, v4 D6): terapéutica, médica, psicológica, abandono, derivación | TC-CEPA-014-005 | RN-2 |
| CEPA-014 | BR | RN-5 | Todo cambio de estado/alta queda registrado en el log de auditoría con autor y fecha | TC-CEPA-014-006 | RN-5 |
| CEPA-014 | TC | TC-014-05 | Cerrar caso con flag de revisión activo; el caso cerrado conserva el flag | TC-CEPA-014-007 | RN-3 |
| CEPA-014 | TC | TC-014-06 | Usuario perfil Auditor intenta cerrar/dar de alta un caso; acceso denegado | TC-CEPA-014-008 |  |
| CEPA-015 | AC | CA-1 | Dado un paciente/ingreso, cuando se registra una ODA con fecha de vencimiento, el sistema la guarda vinculada al folio | TC-CEPA-015-001 | RN-1, RN-2 |
| CEPA-015 | AC | CA-2 | Dada una ODA con vencimiento próximo, cuando corre el proceso de alertas, se genera alerta visible de 'ODA por vencer' | TC-CEPA-015-002 | RN-3 |
| CEPA-015 | AC | CA-3 | Dada una ODA existente, cuando se registra una ODA actualizada, se conserva el historial y se refleja la vigente | TC-CEPA-015-003 | RN-5 |
| CEPA-015 | BR | RN-2 | Cada ODA registra al menos documento/identificador y fecha de vencimiento, vinculada al folio del paciente | TC-CEPA-015-004 | RN-2 |
| CEPA-015 | BR | RN-4 | El reporte de ODAS vencidas queda fuera de esta historia (corresponde a EPIC-09) | TC-CEPA-015-005 | RN-3, RN-4 |
| CEPA-015 | TC | TC-015-03 | ODA que vence hoy; alerta generada en el límite de vigencia | TC-CEPA-015-006 | RN-3 |
| CEPA-015 | TC | TC-015-06 | Usuario perfil Auditor intenta registrar/editar ODA; acceso denegado | TC-CEPA-015-007 |  |
| CEPA-016 | AC | CA-1 | Dado un ingreso sin consentimiento firmado, cuando se intenta iniciar tratamiento, el sistema bloquea e indica obligatoriedad | TC-CEPA-016-001 | RN-1, RN-2 |
| CEPA-016 | AC | CA-2 | Dado un ingreso con consentimiento firmado, cuando se inicia tratamiento, el validador marca cumplido y permite continuar | TC-CEPA-016-002 | RN-1, RN-2 |
| CEPA-016 | AC | CA-3 | Dado un ingreso con consentimiento pendiente, cuando corren las alertas de protocolo, se genera alerta de consentimiento pendiente | TC-CEPA-016-003 | RN-3 |
| CEPA-016 | AC | CA-4 | Dado el formulario de consentimiento, cuando se registra el estado, el sistema permite indicar/adjuntar la evidencia según el mecanismo definido | TC-CEPA-016-004 | RN-4 |
| CEPA-016 | BR | RN-5 | El estado del consentimiento y su evidencia quedan en el log de auditoría | TC-CEPA-016-005 | RN-5 |
| CEPA-016 | TC | TC-016-04 | Consentimiento marcado firmado sin evidencia adjunta; comportamiento según mecanismo definido (nota D9) | TC-CEPA-016-006 | RN-4 |
| CEPA-016 | TC | TC-016-05 | Usuario perfil Auditor intenta cambiar estado de consentimiento; acceso denegado (solo lectura) | TC-CEPA-016-007 |  |
| CEPA-020 | AC | CA-1 | Dado formulario de nuevo registro farmacológico, cuando selecciona un folio existente, entonces el sistema pre-llena los datos básicos heredados y permite confirmarlos. | TC-CEPA-020-001 | RN-1, RN-2 |
| CEPA-020 | AC | CA-2 | Dado que completa médico tratante y estado del caso, cuando guarda, entonces el registro queda vinculado al folio y visible desde Ingresos. | TC-CEPA-020-002 | RN-1, RN-3 |
| CEPA-020 | AC | CA-3 | Dado que intenta crear un registro sin folio asociado, cuando hace clic en guardar, entonces el sistema muestra error de campo obligatorio sin perder los datos ingresados. | TC-CEPA-020-003 | RN-1 |
| CEPA-020 | BR | RN-3 | Médico tratante asignado y estado del caso farmacológico son campos obligatorios. | TC-CEPA-020-004 | RN-3 |
| CEPA-020 | BR | RN-4 | Un folio puede tener a lo sumo un registro farmacológico activo; un reingreso con el mismo folio reutiliza/reactiva el registro asociado. | TC-CEPA-020-005 | RN-4 |
| CEPA-020 | BR | RN-5 | RBAC — solo Administrativo (y Coordinación) puede crear/editar; Auditor solo lectura; el perfil Clínico no existe (D1). | TC-CEPA-020-006 | RN-5 |
| CEPA-020 | BR | RN-6 | Toda operación CRUD queda registrada en el log de auditoría (quién, qué, cuándo). | TC-CEPA-020-007 | RN-6 |
| CEPA-020 | PLANILLA | Gestión de Fármacos | Hoja 'Gestión de Fármacos' (21 columnas): columnas base Folio, Mes, Región de derivación, Fecha Ingreso, Nombre del paciente, Rut, Médico Tratante, Estado. | TC-CEPA-020-008 | RN-2, RN-3 |
| CEPA-021 | AC | CA-1 | Dado el registro farmacológico de un folio, cuando ingresa antecedentes previos de SM y tratamiento previo, entonces el sistema guarda el historial estructurado vinculado al folio. | TC-CEPA-021-001 | RN-4 |
| CEPA-021 | AC | CA-2 | Dado que registra una indicación actual, cuando especifica medicamento, dosis y frecuencia y guarda, entonces se crea una entrada del esquema farmacológico vigente. | TC-CEPA-021-002 | RN-1 |
| CEPA-021 | AC | CA-3 | Dado un medicamento fuera del catálogo, cuando se marca como fármaco extra-sistema y guarda, entonces el sistema acepta el registro y lo identifica como extra-sistema. | TC-CEPA-021-003 | RN-3 |
| CEPA-021 | BR | RN-1 | Cada entrada de indicación actual del esquema requiere medicamento, dosis y frecuencia. | TC-CEPA-021-004 | RN-1 |
| CEPA-021 | BR | RN-2 | El esquema es versionable: una nueva indicación no borra la anterior, se mantiene el historial completo por folio. | TC-CEPA-021-005 | RN-2 |
| CEPA-021 | BR | RN-5 | RBAC — Administrativo/Coordinación editan; Auditor solo lectura. | TC-CEPA-021-006 | RN-5 |
| CEPA-021 | BR | RN-6 | Operaciones CRUD registradas en log de auditoría. | TC-CEPA-021-007 | RN-6 |
| CEPA-022 | AC | CA-1 | Dado que registra una nueva receta, cuando guarda, entonces la receta aparece vinculada al folio y es visible desde el módulo de Ingresos (PRD §7.2.5). | TC-CEPA-022-001 | RN-1, RN-2 |
| CEPA-022 | AC | CA-2 | Dado receta con fecha de revisión dentro de los próximos 5 días, cuando el sistema ejecuta su proceso de alertas, entonces se genera una alerta visible en el panel del administrativo asignado (PRD §7.2.5, D1). | TC-CEPA-022-002 | RN-3, RN-4 |
| CEPA-022 | BR | RN-3 | El proceso genera alerta cuando fecha_revisión está dentro de los próximos 5 días respecto de la fecha de ejecución. | TC-CEPA-022-003 | RN-3 |
| CEPA-022 | BR | RN-4 | Redirección de alerta (D1): la alerta se dirige al administrativo asignado (in-app; correo solo para alertas según D12); el médico tratante es dato informativo sin notificación. | TC-CEPA-022-004 | RN-4 |
| CEPA-022 | BR | RN-5 | Fecha de revisión no puede ser anterior a la fecha de emisión; fecha de envío no anterior a la emisión. | TC-CEPA-022-005 | RN-5, RN-1 |
| CEPA-022 | BR | RN-6 | RBAC — Administrativo/Coordinación gestionan recetas; Auditor solo lectura. | TC-CEPA-022-006 | RN-6 |
| CEPA-022 | BR | RN-7 | Operaciones CRUD registradas en log de auditoría. | TC-CEPA-022-007 | RN-7 |
| CEPA-022 | PLANILLA | Gestión de Fármacos | Hoja 'Gestión de Fármacos': columnas ANTECEDENTES PREVIOS DE SM, TRATAMIENTO FARMACOLÓGICO PREVIO, INDICACIÓN FARMACOLÓGICA ACTUAL, Fecha receta, Fecha Revisión Receta, Fecha Envío Receta (Ahumada), Fecha Gestión Receta (Socorro) 1-3, MARCA. | TC-CEPA-022-008 | RN-1 |
| CEPA-023 | AC | CA-1 | Dado que marca 'disminución de fármacos = Sí', cuando guarda, entonces el sistema exige el detalle del plan de disminución antes de confirmar. | TC-CEPA-023-001 | RN-1 |
| CEPA-023 | AC | CA-2 | Dado que marca 'cambio de esquema = Sí', cuando guarda, entonces el sistema exige el detalle del nuevo esquema antes de confirmar. | TC-CEPA-023-002 | RN-2 |
| CEPA-023 | AC | CA-3 | Dado observaciones y banderas en 'No', cuando guarda, entonces el seguimiento queda vinculado al folio y visible desde Ingresos sin exigir detalles adicionales. | TC-CEPA-023-003 | RN-3, RN-4 |
| CEPA-023 | BR | RN-1 | Si 'disminución de fármacos = Sí', el plan de disminución (texto) es obligatorio (flujo positivo con plan informado, TC-023-01). | TC-CEPA-023-004 | RN-1, RN-4 |
| CEPA-023 | BR | RN-5 | RBAC — Administrativo/Coordinación editan; Auditor solo lectura. | TC-CEPA-023-005 | RN-5 |
| CEPA-023 | BR | RN-6 | Operaciones CRUD registradas en log de auditoría. | TC-CEPA-023-006 | RN-6 |
| CEPA-023 | PLANILLA | Gestión de Fármacos | Hoja 'Gestión de Fármacos': columnas OBSERVACIONES, DISMINUCION DE FARMACOS SI/NO, CAMBIO DE ESQUEMA SI/NO como catálogos cerrados. | TC-CEPA-023-007 | RN-1, RN-2, RN-3 |
| CEPA-030 | AC | CA-1 | Dado formulario de nuevo caso EPT, cuando completa obligatorios y guarda, entonces crea el caso, visible en listado/búsquedas y auditado. | TC-CEPA-030-001 | RN-1, RN-3, RN-7 |
| CEPA-030 | AC | CA-2 | Dado RUT con DV inválido, cuando intenta guardar, entonces error específico, no guarda y conserva demás datos. | TC-CEPA-030-002 | RN-2 |
| CEPA-030 | AC | CA-3 | Dado datos del empleador, cuando agrega correos de coordinación, entonces permite hasta 2 contactos, valida formato y rechaza el tercero. | TC-CEPA-030-003 | RN-4 |
| CEPA-030 | AC | CA-4 | Dado 'Corresponde EPT', cuando selecciona 'No', entonces el caso queda 'No corresponde EPT' y se puede cerrar sin datos de gestión. | TC-CEPA-030-004 | RN-1, RN-5 |
| CEPA-030 | AC | CA-5 | Dado usuario Auditor o Coordinación, cuando abre un caso EPT, entonces visualiza todo en solo lectura sin opciones de edición. | TC-CEPA-030-005 | RN-6 |
| CEPA-030 | BR | RN-1 | Campos obligatorios del caso: folio, mes, fecha de ingreso, nombre, RUT, región, EISTA, factor de riesgo y 'Corresponde EPT'. | TC-CEPA-030-006 | RN-1 |
| CEPA-030 | BR | RN-3 | El folio se vincula al folio del paciente/caso del módulo de Ingresos; un caso EPT pertenece a un único folio. | TC-CEPA-030-007 | RN-3 |
| CEPA-030 | BR | RN-7 | Toda creación/edición de caso EPT se registra en el log de auditoría (quién, qué, cuándo). | TC-CEPA-030-008 | RN-7 |
| CEPA-030 | PLANILLA | Seguimiento EPT | Hoja 'Seguimiento EPT' (27 columnas): columnas de identificación del caso y del empleador. | TC-CEPA-030-009 | RN-1, RN-4 |
| CEPA-031 | AC | CA-1 | Dado caso con Corresponde EPT = Sí, cuando registra plazos de evidencia e insumos, entonces los guarda y muestra en la vista del proceso. | TC-CEPA-031-001 | RN-1, RN-4 |
| CEPA-031 | AC | CA-2 | Dado caso en gestión, cuando indica testigos Sí y cantidad, entonces exige cantidad ≥ 1; con 'No' deshabilita y deja cantidad en cero. | TC-CEPA-031-002 | RN-2 |
| CEPA-031 | AC | CA-3 | Dado caso en gestión, cuando registra número de entrevistas, entonces acepta solo enteros ≥ 0 y actualiza el avance. | TC-CEPA-031-003 | RN-3 |
| CEPA-031 | AC | CA-4 | Dado caso en gestión, cuando registra insumos del EISTA/documentos de incumplimiento y observaciones, entonces guarda vinculado al caso con traza en auditoría. | TC-CEPA-031-004 | RN-5, RN-7 |
| CEPA-031 | AC | CA-5 | Dado caso con Corresponde EPT = No, cuando intenta abrir la gestión del proceso, entonces no exige datos y muestra el caso como no aplicable. | TC-CEPA-031-005 | RN-1 |
| CEPA-031 | BR | RN-4 | Los plazos (evidencia del denunciante, insumos de la empresa) son fechas y no pueden ser anteriores a la fecha de ingreso del caso. | TC-CEPA-031-006 | RN-4 |
| CEPA-031 | BR | RN-6 | Solo Administrativo edita la gestión del proceso; Coordinación y Auditor solo lectura. | TC-CEPA-031-007 | RN-6 |
| CEPA-031 | PLANILLA | Seguimiento EPT | Hoja 'Seguimiento EPT': columnas de gestión operativa del proceso (plazos, testigos, insumos, entrevistas, observaciones). | TC-CEPA-031-008 | RN-2, RN-3, RN-5 |
| CEPA-032 | AC | CA-1 | Dado caso con Corresponde EPT = Sí, cuando registra plazo informe EPT, plazo portal ISL y fecha entrega ISL, entonces guarda y calcula estado de cumplimiento. | TC-CEPA-032-001 | RN-1, RN-3 |
| CEPA-032 | AC | CA-2 | Dado caso con plazo próximo a vencer, cuando corre la revisión programada, entonces genera alerta in-app para el administrativo asignado (reglas EPIC-10). | TC-CEPA-032-002 | RN-1, RN-2 |
| CEPA-032 | AC | CA-3 | Dado informe ya enviado, cuando registra fecha de envío y estado 'enviado', entonces marca el plazo cumplido y cesan las alertas del hito. | TC-CEPA-032-003 | RN-1, RN-4 |
| CEPA-032 | AC | CA-4 | Dado caso con fecha de entrega ISL pasada sin envío, cuando evalúa los plazos, entonces marca 'vencido' y lo expone en el reporte de cumplimiento. | TC-CEPA-032-004 | RN-1 |
| CEPA-032 | AC | CA-5 | Dado usuario Coordinación o Auditor, cuando consulta plazos y estados, entonces los visualiza en solo lectura sin poder editarlos. | TC-CEPA-032-005 | RN-6 |
| CEPA-032 | BR | RN-3 | La fecha de entrega ISL no puede ser anterior a la fecha de ingreso del caso ni al plazo de informe EPT. | TC-CEPA-032-006 | RN-3 |
| CEPA-032 | BR | RN-5 | El cumplimiento de plazos ISL es dato regulatorio: todo cambio de plazo, fecha de envío o estado queda en el log de auditoría. | TC-CEPA-032-007 | RN-5 |
| CEPA-032 | BR | RN-7 | Los casos con 'Corresponde EPT' = No no generan plazos ni alertas EPT. | TC-CEPA-032-008 | RN-7 |
| CEPA-032 | PLANILLA | Seguimiento EPT | Hoja 'Seguimiento EPT': columnas de plazos regulatorios y envío (Plazo Informe EPT, Plazo Portal ISL, Fecha Entrega ISL, Fecha de envío / estado). | TC-CEPA-032-009 | RN-1, RN-3 |
| CEPA-040 | AC | CA-1 | Dado formulario de nuevo caso, cuando ingresa RUT válido existente, entonces pre-llena datos desde el folio y permite confirmar o actualizar. | TC-CEPA-040-001 | RN-1, RN-4 |
| CEPA-040 | AC | CA-2 | Dado campos obligatorios completos, cuando guarda, entonces el caso queda vinculado al folio y visible desde Ingresos y gestión de reintegro. | TC-CEPA-040-002 | RN-1, RN-2 |
| CEPA-040 | AC | CA-3 | Dado RUT con DV inválido, cuando hace clic en guardar, entonces muestra error específico de RUT y conserva el resto de los datos. | TC-CEPA-040-003 | RN-2 |
| CEPA-040 | AC | CA-4 | Dado que selecciona tipo de derivación, cuando abre la lista, entonces solo se ofrecen los valores reales de D4 y 'convenio SOCORRO' no aparece. | TC-CEPA-040-004 | RN-3 |
| CEPA-040 | BR | RN-1 | El folio es la clave de vinculación con Ingresos; un caso de reintegro siempre pertenece a un folio existente o a un reingreso que mantiene el folio anterior (D2). | TC-CEPA-040-005 | RN-1 |
| CEPA-040 | BR | RN-2 | RUT obligatorio y validado por DV; folio, tipo de derivación, fecha, nombre y región son obligatorios (D6). | TC-CEPA-040-006 | RN-2 |
| CEPA-040 | BR | RN-4 | Sexo, edad/tramo etario y zona geográfica (región, comuna) son obligatorios para datos limpios y comparables (D5/D6) y alimentan los filtros del dashboard. | TC-CEPA-040-007 | RN-2, RN-4 |
| CEPA-040 | BR | RN-5 | Toda operación de creación/edición se registra en el log de auditoría (quién, qué, cuándo). | TC-CEPA-040-008 | RN-5 |
| CEPA-040 | BR | RN-6 | Solo Administrativo y Coordinación pueden crear/editar; Auditor solo lectura. | TC-CEPA-040-009 | RN-6 |
| CEPA-040 | PLANILLA | Seguimiento Reintegro | Hoja 'Seguimiento Reintegro' (24 columnas): FOLIO, DERIVACIÓN, FECHA, NOMBRE, RUT, REGION. | TC-CEPA-040-010 | RN-1, RN-2 |
| CEPA-041 | AC | CA-1 | Dado caso sin RECA, cuando ingresa fecha, tipo y N° de RECA y guarda, entonces la RECA queda asociada y visible en reintegro y auditoría. | TC-CEPA-041-001 | RN-1, RN-5 |
| CEPA-041 | AC | CA-2 | Dado solicitud de medidas = Sí, cuando intenta guardar sin describir medidas ni su fecha, entonces el sistema exige detalle y fecha antes de guardar. | TC-CEPA-041-002 | RN-2 |
| CEPA-041 | AC | CA-3 | Dado medida con fecha registrada, cuando se registra la verificación, entonces la fecha de verificación debe ser >= fecha de la medida; en caso contrario se rechaza. | TC-CEPA-041-003 | RN-3, RN-4 |
| CEPA-041 | AC | CA-4 | Dado caso con riesgos calificados, cuando el Auditor consulta el caso, entonces visualiza RECA, riesgos y estado de medidas en modo solo lectura. | TC-CEPA-041-004 | RN-6 |
| CEPA-041 | BR | RN-1 | N° de RECA único por caso; fecha y tipo de RECA obligatorios cuando se registra una RECA. | TC-CEPA-041-005 | RN-1 |
| CEPA-041 | BR | RN-4 | Verificación = Sí requiere fecha de verificación registrada. | TC-CEPA-041-006 | RN-3, RN-4 |
| CEPA-041 | BR | RN-5 | Razón social del empleador obligatoria; consistente con el rubro/actividad económica de CEPA-040. | TC-CEPA-041-007 | RN-5 |
| CEPA-041 | BR | RN-6 | Toda operación se registra en el log de auditoría. Solo Administrativo/Coordinación editan; Auditor solo lectura. | TC-CEPA-041-008 | RN-6 |
| CEPA-041 | PLANILLA | Seguimiento Reintegro | Hoja 'Seguimiento Reintegro' (24 columnas): SOLICITAR RECA, FECHA RECA, RECA, N° RECA, SOLICITAR-VERIFICACIÓN-MEDIDAS, SOLICITUDES REALIZADAS, FECHA MEDIDAS, FECHA VERIFICACION, RIESGOS, RAZON SOCIAL. | TC-CEPA-041-009 | RN-1, RN-2, RN-3 |
| CEPA-042 | AC | CA-1 | Dado caso con RECA y medidas verificadas, cuando marca estado Total e ingresa fecha de reintegro, entonces registra término de LM y refleja 'reintegro total' en reintegro y auditoría. | TC-CEPA-042-001 | RN-1, RN-3 |
| CEPA-042 | AC | CA-2 | Dado estado = Parcial, cuando se guarda sin fecha de reintegro, entonces el sistema permite guardar pero mantiene el caso abierto. | TC-CEPA-042-002 | RN-1, RN-3 |
| CEPA-042 | AC | CA-3 | Dado caso con reintegro total, cuando registra alta médica y psicológica con tipo de alta, entonces el caso queda cerrado y la fecha de reintegro no puede ser anterior a la fecha de RECA. | TC-CEPA-042-003 | RN-2, RN-4 |
| CEPA-042 | AC | CA-4 | Dado caso remitido a ISL = Sí, cuando el Auditor consulta el cierre, entonces visualiza estado, fechas y altas en modo solo lectura. | TC-CEPA-042-004 | RN-5, RN-6 |
| CEPA-042 | BR | RN-1 | Estado de reintegro en {pendiente, parcial, total}; 'Total' exige fecha de reintegro (término de LM). | TC-CEPA-042-005 | RN-1, RN-3 |
| CEPA-042 | BR | RN-2 | Fecha de reintegro >= fecha de RECA (CEPA-041) y >= fecha del caso (CEPA-040). | TC-CEPA-042-006 | RN-2 |
| CEPA-042 | BR | RN-4 | El cierre requiere al menos alta médica o psicológica con tipo de alta; tipo de alta obligatorio al cerrar (D11). | TC-CEPA-042-007 | RN-4 |
| CEPA-042 | BR | RN-5 | 'Remitido a ISL' es sí/no; si Sí, queda disponible para el reporte de auditoría/contraparte. | TC-CEPA-042-008 | RN-5 |
| CEPA-042 | BR | RN-6 | Toda operación se registra en el log de auditoría. Solo Administrativo/Coordinación editan; Auditor solo lectura. | TC-CEPA-042-009 | RN-6 |
| CEPA-042 | PLANILLA | Seguimiento Reintegro | Hoja 'Seguimiento Reintegro' (24 columnas): REINTEGRO, FECHA REINTEGRO (T.LM), REMITIDO A ISL, ESTADO, ALTA MEDICA/CIERRE, ALTA PSICOLOGICA/CIERRE, TIPO DE ALTA, OBSERVACIÓN. | TC-CEPA-042-010 | RN-1, RN-4, RN-5 |
| CEPA-050 | AC | CA-1 | Dado un Auditor que busca un caso por folio/RUT/nº siniestro, cuando abre la vista consolidada, entonces ve §7.5.1–§7.5.4 en una sola pantalla consolidados desde los módulos de origen. | TC-CEPA-050-001 | RN-1, RN-3 |
| CEPA-050 | AC | CA-2 | Dado un usuario con dos denuncias bajo el mismo RUT con distinto nº de siniestro (D2), cuando el Auditor abre la vista consolidada, entonces cada siniestro se presenta como caso diferenciado sin mezclar hitos. | TC-CEPA-050-002 | RN-3 |
| CEPA-050 | AC | CA-3 | Dado un caso con diagnóstico inicial y post-RECA distintos, cuando el Auditor revisa el seguimiento de evaluaciones, entonces ve ambos diagnósticos por separado junto con la fecha de calificación. | TC-CEPA-050-003 | RN-4 |
| CEPA-050 | AC | CA-4 | Dado un Auditor en la vista consolidada, cuando intenta modificar cualquier dato clínico, entonces no hay controles de edición y la acción queda denegada (solo lectura). | TC-CEPA-050-004 | RN-1, RN-2 |
| CEPA-050 | AC | CA-5 | Dado un caso en tratamiento sin altas, cuando el Auditor abre la vista consolidada, entonces el cierre se muestra pendiente/vacío sin bloquear la visualización del resto de los hitos. | TC-CEPA-050-005 | RN-6 |
| CEPA-050 | BR | RN-5 | Coherencia temporal de hitos: denuncia ≤ derivación ≤ evaluaciones ≤ calificación ≤ 1ª consulta ≤ altas; la auditoría señala inconsistencias, no las corrige. | TC-CEPA-050-006 | RN-5, RN-1 |
| CEPA-050 | BR | RN-6 | El cierre puede tener altas parciales (solo médica, solo psicológica) o terapéutica; la simplificación a una sola fecha de alta queda sujeta a D11. | TC-CEPA-050-007 | RN-6 |
| CEPA-050 | BR | RN-7 | El acceso a la vista consolidada se registra en el log de auditoría (EPIC-00); solo Coordinación y Auditor acceden; Administrativo según permisos de sus módulos. | TC-CEPA-050-008 | RN-7, RN-2 |
| CEPA-050 | PLANILLA | Auditoría | Hoja Excel 'Auditoría' (28 columnas, A1:AB12) reemplazada por el módulo de auditoría. | TC-CEPA-050-009 | RN-1, RN-3 |
| CEPA-050 | PLANILLA | Auditoría | Valores de lista de la hoja 'Auditoría': sí/no en reintegros y altas, catálogo de Estado y marcador sin-dato 'S/D' observado en filas 5–8. | TC-CEPA-050-010 | RN-6 |
| CEPA-051 | AC | CA-1 | Dado el generador de reportes, cuando el Auditor selecciona período + diagnóstico + profesional + estado y ejecuta, entonces devuelve solo los casos que cumplen todos los filtros con sus hitos consolidados. | TC-CEPA-051-001 | RN-2, RN-6 |
| CEPA-051 | AC | CA-2 | Dado un reporte generado con filtros, cuando el Auditor solicita la descarga, entonces recibe un formato estándar descargable con los filtros como metadatos. | TC-CEPA-051-002 | RN-4 |
| CEPA-051 | AC | CA-3 | Dado un reporte descargado, cuando la contraparte verifica un dato, entonces cada fila es trazable a su folio y nº de siniestro y hasta su módulo fuente. | TC-CEPA-051-003 | RN-3 |
| CEPA-051 | AC | CA-4 | Dado filtros sin coincidencias, cuando el Auditor ejecuta el reporte, entonces ve un resultado vacío con mensaje claro, sin error ni filas espurias. | TC-CEPA-051-004 |  |
| CEPA-051 | AC | CA-5 | Dado un perfil sin permiso de auditoría, cuando intenta generar o descargar un reporte, entonces el sistema deniega la acción por RBAC. | TC-CEPA-051-005 | RN-7 |
| CEPA-051 | BR | RN-1 | Los reportes son de solo lectura: el Auditor genera y descarga, no edita datos clínicos (D1 · PRD §5.3). | TC-CEPA-051-006 | RN-1, RN-7 |
| CEPA-051 | BR | RN-2 | Los filtros son combinables (AND); un período es obligatorio para acotar el universo del reporte. | TC-CEPA-051-007 | RN-2 |
| CEPA-051 | BR | RN-5 | La generación de cada reporte se registra en el log de auditoría (EPIC-00): quién generó qué reporte, con qué filtros y cuándo. | TC-CEPA-051-008 | RN-5 |
| CEPA-051 | BR | RN-6 | Filtros y dimensiones alineados a D5: diagnósticos, tipos de alta, profesional, programa, estado del caso, zona geográfica. | TC-CEPA-051-009 | RN-6, RN-2 |
| CEPA-051 | TC | TC-051-05 | Borde: período amplio (anual) con alto volumen (~800 casos) → reporte paginado/completo en <2 s y descarga íntegra. | TC-CEPA-051-010 | RN-4 |
| CEPA-060 | AC | CA-1 | Dado un administrativo en el formulario de nuevo control, cuando ingresa folio, región, fecha ingreso, paciente, RUT y médico y guarda, entonces el control se persiste vinculado al folio y se muestra en la vista de gestión. | TC-CEPA-060-001 | RN-1, RN-5 |
| CEPA-060 | AC | CA-2 | Dado un control con fecha de ingreso y fecha de control, cuando se guarda, entonces el sistema calcula automáticamente la semana del control y la muestra solo lectura. | TC-CEPA-060-002 | RN-3 |
| CEPA-060 | AC | CA-3 | Dado que se ingresa un RUT con DV inválido, cuando hace clic en guardar, entonces se muestra error específico sin perder los datos ingresados. | TC-CEPA-060-003 | RN-2 |
| CEPA-060 | AC | CA-4 | Dado un folio que no corresponde a ningún paciente con ingreso, cuando intenta guardar, entonces el sistema bloquea e informa que debe asociarse a un folio existente. | TC-CEPA-060-004 | RN-1 |
| CEPA-060 | BR | RN-4 | Borde: si fecha_control = fecha_ingreso, la semana del control es 1. | TC-CEPA-060-005 | RN-3, RN-4 |
| CEPA-060 | BR | RN-4 | Si fecha_control < fecha_ingreso, el sistema rechaza el registro. | TC-CEPA-060-006 | RN-4 |
| CEPA-060 | BR | RN-5 | Campos obligatorios: folio, región de derivación, fecha de ingreso, nombre, RUT, médico tratante (Decisiones v4 · D6). | TC-CEPA-060-007 | RN-5 |
| CEPA-060 | BR | RN-6 | Coordinación y Administrativo pueden crear/editar; Auditor solo lectura. | TC-CEPA-060-008 | RN-6 |
| CEPA-060 | PLANILLA | Controles Médicos | Hoja «Controles Médicos» (24 columnas): Folio, Región de derivación, Fecha Ingreso, Paciente, Rut, Médico Tratante, Semana Control, Día Próximo Control, Agenda Salutem, Licencia Si/No, Resumen (Término LM), Total días de LM, Tipo Licencia, Tipo Reposo, GAF, RECA, fechas RECA EP/EC, Fecha Cierre EC, Observaciones generales. | TC-CEPA-060-009 |  |
| CEPA-061 | AC | CA-1 | Dado un control registrado, cuando el administrativo ingresa el día del próximo control y guarda, entonces el sistema almacena la fecha asociada al folio. | TC-CEPA-061-001 | RN-1 |
| CEPA-061 | AC | CA-2 | Dado que programa un próximo control, cuando indica el estado de agenda (sí/no), entonces se persiste; por defecto 'no' hasta confirmar la agenda en SALUTEM/SAM. | TC-CEPA-061-002 | RN-2 |
| CEPA-061 | AC | CA-3 | Dado un próximo control dentro de la ventana de alerta, cuando el sistema ejecuta su revisión programada, entonces se genera una alerta in-app para el administrativo asignado. | TC-CEPA-061-003 | RN-3 |
| CEPA-061 | AC | CA-4 | Dado que ingresa un próximo control anterior a la fecha del control actual, cuando intenta guardar, entonces el sistema rechaza e informa que debe ser posterior. | TC-CEPA-061-004 | RN-1 |
| CEPA-061 | BR | RN-4 | Un folio puede tener a lo más un próximo control vigente; programar uno nuevo reemplaza/cierra el anterior pendiente. | TC-CEPA-061-005 | RN-4 |
| CEPA-061 | BR | RN-5 | Coordinación y Administrativo pueden programar/editar; Auditor solo lectura. | TC-CEPA-061-006 | RN-5 |
| CEPA-062 | AC | CA-1 | Dado un control con Licencia=sí, cuando ingresa término LM, total días, tipo de licencia, tipo de reposo y GAF y guarda, entonces se persisten asociados al control. | TC-CEPA-062-001 | RN-1, RN-2, RN-4 |
| CEPA-062 | AC | CA-2 | Dado un control con Licencia=no, cuando se guarda, entonces el sistema no exige los campos de licencia y los deja vacíos/no aplica. | TC-CEPA-062-002 | RN-1 |
| CEPA-062 | AC | CA-3 | Dado que se ingresa el GAF, cuando el valor está fuera del rango 0–100, entonces el sistema lo rechaza e informa el rango válido. | TC-CEPA-062-003 | RN-3 |
| CEPA-062 | AC | CA-4 | Dado que registra el estado RECA y observaciones generales, cuando guarda el control, entonces se persisten y son visibles en la vista de gestión y para el Auditor. | TC-CEPA-062-004 | RN-5 |
| CEPA-062 | BR | RN-1 | Si licencia=sí, resumen de término, total de días, tipo de licencia y tipo de reposo son obligatorios; si licencia=no, se omiten. | TC-CEPA-062-005 | RN-1 |
| CEPA-062 | BR | RN-2 | tipo_reposo ∈ {total, parcial}; total_días_LM es entero ≥ 1. | TC-CEPA-062-006 | RN-2 |
| CEPA-062 | BR | RN-4 | tipo_licencia toma valores del catálogo de tipos de LM (ej. tipo 1, 5, 6 — consistente con §7.7.1). | TC-CEPA-062-007 | RN-4 |
| CEPA-062 | BR | RN-5 | El estado RECA y las observaciones generales son siempre editables independientemente del valor de licencia. | TC-CEPA-062-008 | RN-1, RN-5 |
| CEPA-062 | BR | RN-6 | Coordinación y Administrativo editan; Auditor solo lectura (PRD §5.3). | TC-CEPA-062-009 | RN-6 |
| CEPA-062 | PLANILLA | Controles Médicos | Columnas tipo lista de la hoja «Controles Médicos»: Licencia Si/No, Agenda Salutem, Tipo Reposo, Tipo Licencia deben ser catálogos cerrados. | TC-CEPA-062-010 | RN-2, RN-4 |
| CEPA-070 | AC | CA-1 | Dado formulario de nueva LM con paciente seleccionado, cuando completa los obligatorios y guarda, entonces la LM queda registrada, vinculada al folio y visible en el historial. | TC-CEPA-070-001 | RN-1, RN-6 |
| CEPA-070 | AC | CA-2 | Dado fin < inicio, cuando intenta guardar, entonces error de validación específico, no guarda y conserva los datos. | TC-CEPA-070-002 | RN-4 |
| CEPA-070 | AC | CA-3 | Dado días, inicio y fin de reposo, cuando la cantidad no coincide con la diferencia de fechas, entonces el sistema advierte antes de permitir el guardado. | TC-CEPA-070-003 | RN-2, RN-5 |
| CEPA-070 | AC | CA-4 | Dado un RUT con DV inválido, cuando se intenta guardar la LM, entonces el sistema bloquea el guardado con mensaje de RUT inválido. | TC-CEPA-070-004 | RN-1 |
| CEPA-070 | BR | RN-2 | Campos adicionales obligatorios v4 D8: días de reposo, inicio del reposo, fecha de emisión, fin del reposo, indicación de reposo, diagnóstico. | TC-CEPA-070-005 | RN-2 |
| CEPA-070 | BR | RN-3 | tipo_de_LM solo admite {1, 5, 6}; tipo_de_reposo solo admite {total, parcial}. | TC-CEPA-070-006 | RN-3 |
| CEPA-070 | BR | RN-4 | fecha_termino ≥ fecha_inicio; fin_reposo ≥ inicio_reposo; fecha_emision ≤ fecha_inicio. | TC-CEPA-070-007 | RN-4 |
| CEPA-070 | BR | RN-6 | La LM se vincula al folio del paciente existente; no se crea LM sin folio asociado. | TC-CEPA-070-008 | RN-6 |
| CEPA-070 | BR | RN-7 | Toda operación CRUD se registra en el log de auditoría (quién, qué, cuándo) — PRD §7.13. | TC-CEPA-070-009 | RN-7 |
| CEPA-070 | TC | TC-070-06 | Usuario perfil Auditor intenta abrir/guardar formulario de nueva LM → acceso de solo lectura, creación denegada (RBAC). | TC-CEPA-070-010 |  |
| CEPA-070 | PLANILLA | Licencias Médicas | Hoja 'Licencias Médicas' (15 columnas, 1584 filas): Región, Paciente, Rut, Folio, Días, Inicio, Termino, Tipo Reposo, Tipo LM, Envio a ISL, EEAG, Tipo LM2, Fecha Emisión LM, Observaciones, Columna1. | TC-CEPA-070-011 | RN-1, RN-2 |
| CEPA-070 | PLANILLA | Licencias Médicas | Columnas tipo lista de la hoja: Tipo Reposo, Tipo LM, Tipo LM2, Envio a ISL; EEAG con rango 1–100. | TC-CEPA-070-012 | RN-3 |
| CEPA-070 | PLANILLA | Licencias Médicas | La hoja tiene 1.584 filas históricas; el módulo debe contemplar paginación e indexación desde el inicio (RNF <2 s). | TC-CEPA-070-013 |  |
| CEPA-071 | AC | CA-1 | Dado paciente con 3 LM previas, cuando guarda una nueva, entonces el sistema calcula el total acumulado sumando las 4 licencias y lo muestra en la vista del paciente. | TC-CEPA-071-001 | RN-1, RN-2 |
| CEPA-071 | AC | CA-2 | Dado licencias extra-sistema registradas (v4 D7), cuando se calcula el acumulado, entonces también se suman al total marcadas como origen extra-sistema. | TC-CEPA-071-002 | RN-1 |
| CEPA-071 | AC | CA-3 | Dado dos licencias solapadas en fechas, cuando se calcula el acumulado, entonces se aplica la regla de no doble-conteo de días calendario y se señala el solapamiento. | TC-CEPA-071-003 | RN-3 |
| CEPA-071 | BR | RN-2 | El recálculo se dispara automáticamente al crear, editar o anular cualquier LM del paciente. | TC-CEPA-071-004 | RN-2, RN-1 |
| CEPA-071 | BR | RN-4 | Una LM anulada/rechazada (ej. 77 BIS) se excluye del acumulado vigente pero se mantiene en el historial. | TC-CEPA-071-005 | RN-4, RN-2 |
| CEPA-071 | BR | RN-5 | El acumulado se muestra en la vista consolidada del paciente y alimenta el reporte de LM acumuladas (PRD §7.9). | TC-CEPA-071-006 | RN-5 |
| CEPA-071 | BR | RN-6 | Borde: paciente sin LM previas → acumulado = días de la primera LM registrada. | TC-CEPA-071-007 | RN-6, RN-2 |
| CEPA-071 | TC | TC-071-06 | Usuario perfil Auditor visualiza acumulado → lectura permitida; sin posibilidad de editar LM que lo alteren. | TC-CEPA-071-008 |  |
| CEPA-072 | AC | CA-1 | Dado LM que vence en los próximos 3 días hábiles, cuando corre la revisión programada, entonces se genera alerta visible para el administrativo asignado. | TC-CEPA-072-001 | RN-1, RN-2, RN-4, RN-6 |
| CEPA-072 | AC | CA-2 | Dado que la alerta se generó, cuando el administrativo asignado inicia sesión, entonces la ve en su panel de notificaciones in-app filtrado por rol y pacientes asignados. | TC-CEPA-072-002 | RN-2, RN-3 |
| CEPA-072 | AC | CA-3 | Dado LM ya vencida o anulada, cuando corre la revisión de alertas, entonces no se genera ni se mantiene alerta de 'por vencer'. | TC-CEPA-072-003 | RN-5 |
| CEPA-072 | BR | RN-1 | Umbral: la LM vence dentro de 3 días hábiles (excluye sábados, domingos y festivos) desde la fecha de ejecución de la revisión. | TC-CEPA-072-004 | RN-1 |
| CEPA-072 | BR | RN-2 | El destinatario es el administrativo asignado al caso/paciente; por v4 D1 no se notifica a clínicos. | TC-CEPA-072-005 | RN-2 |
| CEPA-072 | BR | RN-4 | Job diario idempotente: no duplica la alerta si ya existe una activa para la misma LM (alinear con EPIC-10). | TC-CEPA-072-006 | RN-4 |
| CEPA-072 | BR | RN-6 | Meta de negocio: 0% de vencimientos de licencia sin alerta previa (OU4, PRD §3.1). | TC-CEPA-072-007 | RN-6, RN-1, RN-4 |
| CEPA-072 | TC | TC-072-06 | Perfil Clínico sin acceso al sistema (v4 D1): confirmado que no existe destinatario clínico; alerta solo administrativa. | TC-CEPA-072-008 | RN-2 |
| CEPA-073 | AC | CA-1 | Dado LM laboral registrada, cuando el administrativo marca el envío a ISL con estado y fecha, entonces la LM refleja estado (pendiente/enviado/rechazado) y fecha en el historial. | TC-CEPA-073-001 | RN-1, RN-2, RN-7 |
| CEPA-073 | AC | CA-2 | Dado que registra EEAG/GAF, fecha de emisión y observaciones, cuando guarda, entonces quedan asociados a la LM y disponibles para auditoría. | TC-CEPA-073-002 | RN-1, RN-7 |
| CEPA-073 | AC | CA-3 | Dado una LM extra-sistema del paciente (v4 D7), cuando se registra marcada como extra-sistema, entonces aparece en el historial completo y se incluye en los días acumulados. | TC-CEPA-073-003 | RN-3, RN-4 |
| CEPA-073 | AC | CA-4 | Dado un auditor consultando un caso, cuando abre el historial de LM, entonces ve todas las licencias con su trazabilidad ISL en modo solo lectura. | TC-CEPA-073-004 | RN-3, RN-6 |
| CEPA-073 | BR | RN-2 | Estados de envío ISL {pendiente, enviado, rechazado}; fecha_envio_ISL obligatoria cuando estado = enviado o rechazado. | TC-CEPA-073-005 | RN-2 |
| CEPA-073 | BR | RN-1 | Campos de gestión §7.7.2: envio_ISL (estado + fecha), EEAG_GAF (1–100), fecha_emision, observaciones. | TC-CEPA-073-006 | RN-1 |
| CEPA-073 | BR | RN-3 | El historial completo (§7.7.3) lista todas las LM del folio ordenadas cronológicamente con origen, estado de envío y diagnóstico. | TC-CEPA-073-007 | RN-3 |
| CEPA-073 | BR | RN-4 | Las licencias extra-sistema (v4 D7) se distinguen con marca de origen; su estado ISL puede quedar como 'no aplica / externo'. | TC-CEPA-073-008 | RN-4 |
| CEPA-073 | BR | RN-5 | Un rechazo por 77 BIS se refleja en estado y observaciones y dispara la exclusión del acumulado vigente (coordinado con CEPA-071 RN-4). | TC-CEPA-073-009 | RN-5, RN-7 |
| CEPA-073 | BR | RN-6 | Solo perfiles con CRUD (Administrativo, Coordinación) editan la trazabilidad; Auditor es solo lectura (PRD §5.3). | TC-CEPA-073-010 | RN-6 |
| CEPA-073 | BR | RN-7 | Toda actualización de trazabilidad se registra en el log de auditoría. | TC-CEPA-073-011 | RN-7 |
| CEPA-080 | AC | CA-1 | Dado profesional y día hábil, cuando se solicita propuesta diaria, entonces lista ordenada de candidatos dentro de disponibilidad y cupo, excluyendo reposo y priorizando controles/recetas. | TC-CEPA-080-001 | RN-2, RN-3, RN-4 |
| CEPA-080 | AC | CA-2 | Dado profesional y semana objetivo, cuando se solicita propuesta semanal, entonces candidatos distribuidos en días hábiles respetando cupo, sin reposo y balanceando carga. | TC-CEPA-080-002 | RN-3, RN-4 |
| CEPA-080 | AC | CA-3 | Dado profesional y mes objetivo, cuando se solicita propuesta mensual, entonces propuesta consolidada por semanas respetando disponibilidad y periodicidad, con vencidos en prioridad alta. | TC-CEPA-080-003 | RN-2, RN-4 |
| CEPA-080 | AC | CA-4 | Dado paciente con reposo que incluye la fecha candidata, cuando se arma cualquier propuesta, entonces no es propuesto y se indica 'reposo vigente hasta dd/mm/aaaa'. | TC-CEPA-080-004 | RN-1, RN-5 |
| CEPA-080 | AC | CA-5 | Dado paciente con próximo control en la ventana, cuando se genera la propuesta, entonces se incluye y prioriza; vencido sobre próximo, mostrando fecha y estado. | TC-CEPA-080-005 | RN-2 |
| CEPA-080 | AC | CA-6 | Dado paciente con receta reciente que requiere seguimiento, cuando se genera la propuesta, entonces se incluye con etiqueta 'seguimiento de receta' salvo reposo vigente. | TC-CEPA-080-006 | RN-1, RN-6 |
| CEPA-080 | AC | CA-7 | Dado una propuesta generada, cuando el usuario confirma citas, entonces quedan agendadas y cuentan como 'citas agendadas' para adherencia; las descartadas no generan cita. | TC-CEPA-080-007 | RN-8 |
| CEPA-080 | AC | CA-8 | Dado un usuario autenticado, cuando intenta generar/confirmar, entonces solo Administrativo y Coordinación pueden; Auditor solo lectura; otro acceso denegado. | TC-CEPA-080-008 | RN-7 |
| CEPA-080 | BR | RN-1 | Nunca se propone cita en día con reposo vigente; la exclusión por reposo prevalece sobre cualquier criterio de inclusión (control o receta). | TC-CEPA-080-009 | RN-1, RN-6 |
| CEPA-080 | BR | RN-2 | Prioridad: (1) control vencido, (2) control próximo, (3) receta con seguimiento; a igual prioridad, más antiguo primero. | TC-CEPA-080-010 | RN-2 |
| CEPA-080 | BR | RN-3 | La propuesta nunca excede el cupo diario del profesional; el exceso se difiere al siguiente día/semana hábil disponible. | TC-CEPA-080-011 | RN-2, RN-3, RN-4 |
| CEPA-080 | BR | RN-4 | Solo días hábiles (lun–vie) y bloques de disponibilidad del profesional; nunca fines de semana ni fuera de disponibilidad. | TC-CEPA-080-012 | RN-3, RN-4 |
| CEPA-080 | BR | RN-5 | El reposo vigente se evalúa contra la fecha candidata, no contra la fecha de generación; la propuesta mensual excluye reposo día a día. | TC-CEPA-080-013 | RN-1, RN-5 |
| CEPA-080 | BR | RN-6 | 'Receta reciente que requiere seguimiento' se determina por fecha dentro de ventana parametrizable; recetas gestionadas/cerradas no generan candidatura. | TC-CEPA-080-014 | RN-6 |
| CEPA-080 | BR | RN-8 | Cada cita agendada desde propuesta confirmada incrementa el denominador 'citas agendadas'; la realización efectiva alimenta el numerador 'citas realizadas' (D5). | TC-CEPA-080-015 | RN-8 |
| CEPA-080 | BR | RN-9 | Toda generación y confirmación de propuesta queda registrada en el log de auditoría (quién, qué profesional/paciente, cuándo) — PRD §7.13. | TC-CEPA-080-016 | RN-9 |
| CEPA-080 | TC | TC-080-10 | Con volúmenes objetivo (1.500+ licencias, 800+ ingresos, 500+ recetas/año, ~25 profesionales), la propuesta mensual se genera en < 2 s excluyendo reposo día a día. | TC-CEPA-080-017 | RN-1, RN-5 |
| CEPA-090 | AC | CA-1 | Dado que la coordinadora abre el dashboard, cuando la vista carga, entonces muestra indicadores agregados de todos los programas en tiempo real. | TC-CEPA-090-001 | RN-1, RN-4 |
| CEPA-090 | AC | CA-2 | Dado que la coordinadora aplica uno o varios filtros, cuando confirma, entonces todos los indicadores se recalculan al recorte seleccionado. | TC-CEPA-090-002 | RN-2, RN-3 |
| CEPA-090 | AC | CA-3 | Dado un volumen de producción, cuando se carga o filtra el dashboard, entonces el resultado se presenta en menos de 10 segundos (OU3). | TC-CEPA-090-003 | RN-5 |
| CEPA-090 | AC | CA-4 | Dado un usuario Administrativo o Auditor, cuando accede al dashboard, entonces ve los indicadores en solo lectura sin configuración ni edición. | TC-CEPA-090-004 | RN-6 |
| CEPA-090 | BR | RN-7 | Cada métrica del dashboard debe pasar el QA de métricas (validación de resultado y de proceso — D5); no se publica sin validación. | TC-CEPA-090-005 | RN-7 |
| CEPA-090 | TC | TC-090-04 | Aplicar combinación de filtros sin datos → estado vacío explícito, sin error ni cifras erróneas. | TC-CEPA-090-006 | RN-3 |
| CEPA-091 | AC | CA-1 | Dado período y filtros definidos, cuando genera el reporte operativo, entonces produce cifras de citas, atenciones, inasistencias y anulaciones del recorte. | TC-CEPA-091-001 | RN-1 |
| CEPA-091 | AC | CA-2 | Dado un reporte generado, cuando la coordinadora lo descarga, entonces obtiene el archivo en formato estándar (Excel/CSV y PDF) con los datos de pantalla. | TC-CEPA-091-002 | RN-2, RN-3 |
| CEPA-091 | AC | CA-3 | Dado un usuario Auditor, cuando genera/descarga reportes operativos, entonces lo hace en solo lectura sin alterar datos de origen. | TC-CEPA-091-003 | RN-4 |
| CEPA-091 | BR | RN-5 | La generación de reportes queda trazada en el log de auditoría (quién generó qué reporte y cuándo). | TC-CEPA-091-004 | RN-5 |
| CEPA-091 | TC | TC-091-03 | Generar sin definir período → error de validación; no genera reporte. | TC-CEPA-091-005 | RN-1 |
| CEPA-091 | TC | TC-091-04 | Generar reporte de período sin citas → reporte con totales en cero, sin error. | TC-CEPA-091-006 | RN-1 |
| CEPA-091 | TC | TC-091-05 | Intentar generar reporte con perfil sin acceso → acceso denegado. | TC-CEPA-091-007 | RN-4 |
| CEPA-091 | PLANILLA | 7 hojas planilla CEPA | El epic reemplaza la generación manual de indicadores y reportes desde las 7 planillas Excel; los reportes deben reproducir su información. | TC-CEPA-091-008 | RN-1, RN-3 |
| CEPA-092 | AC | CA-1 | Dado convenio y período mensual seleccionados, cuando hace clic en generar, entonces produce el reporte de cumplimiento con los indicadores comprometidos. | TC-CEPA-092-001 | RN-1 |
| CEPA-092 | AC | CA-2 | Dado que quiere acotar el reporte, cuando filtra por profesional, tipo de atención y programa, entonces el reporte se restringe al recorte y permite descarga estándar. | TC-CEPA-092-002 | RN-2, RN-4 |
| CEPA-092 | AC | CA-3 | Dado volúmenes de producción, cuando se solicita el reporte mensual de convenio, entonces se obtiene en menos de 5 minutos (OI2). | TC-CEPA-092-003 | RN-3 |
| CEPA-092 | BR | RN-5 | Tipos de convenio/derivación según valores reales (D4), sin «convenio SOCORRO». | TC-CEPA-092-004 | RN-5 |
| CEPA-092 | BR | RN-6 | RBAC — Coordinación genera; Auditor solo lectura; el perfil Clínico no existe (D1). | TC-CEPA-092-005 | RN-6 |
| CEPA-092 | BR | RN-7 | La generación queda trazada en el log de auditoría. | TC-CEPA-092-006 | RN-7 |
| CEPA-092 | TC | TC-092-04 | Generar reporte de convenio sin actividad → reporte válido con totales en cero. | TC-CEPA-092-007 | RN-1 |
| CEPA-093 | AC | CA-1 | Dado el reporte de carga laboral y un período, cuando lo genera, entonces muestra por profesional el volumen de casos/atenciones asignados. | TC-CEPA-093-001 | RN-1, RN-4 |
| CEPA-093 | AC | CA-2 | Dado que quiere comparar, cuando filtra por especialidad/tipo de atención/programa, entonces recalcula la carga y permite descarga estándar. | TC-CEPA-093-002 | RN-2, RN-3 |
| CEPA-093 | AC | CA-3 | Dado un usuario Auditor, cuando consulta el reporte de carga laboral, entonces lo ve en solo lectura. | TC-CEPA-093-003 | RN-5 |
| CEPA-093 | BR | RN-6 | La métrica de carga debe pasar el QA de métricas (D5). | TC-CEPA-093-004 | RN-6 |
| CEPA-093 | TC | TC-093-03 | Profesional sin casos en el período → listado con carga cero. | TC-CEPA-093-005 | RN-1 |
| CEPA-093 | TC | TC-093-04 | Generar sin definir período → error de validación. | TC-CEPA-093-006 | RN-2 |
| CEPA-093 | BR | RN-4 | El profesional es un dato de referencia, no un usuario con acceso (D1): la carga se atribuye al profesional asignado en el registro. | TC-CEPA-093-007 | RN-4 |
| CEPA-094 | AC | CA-1 | Dado que genera el reporte de licencias acumuladas, cuando lo solicita, entonces muestra por paciente/folio el total de días sumando todas sus licencias. | TC-CEPA-094-001 | RN-1 |
| CEPA-094 | AC | CA-2 | Dado que aplica filtros (período, región/comuna, tipo de licencia, tipo de reposo, programa), cuando confirma, entonces recalcula y permite descarga estándar. | TC-CEPA-094-002 | RN-2, RN-5 |
| CEPA-094 | AC | CA-3 | Dado que existen licencias extra-sistema (D7), cuando se genera el reporte, entonces se incluyen en el acumulado si así se configuró, distinguidas como tales. | TC-CEPA-094-003 | RN-4 |
| CEPA-094 | BR | RN-3 | Datos de licencia conforme a D8 (días de reposo, inicio/fin, emisión, tipo, indicación y diagnóstico, tipo de reposo). | TC-CEPA-094-004 | RN-3, RN-2 |
| CEPA-094 | BR | RN-6 | RBAC — Coordinación genera; Auditor solo lectura; el cálculo acumulado debe pasar el QA de métricas (D5). | TC-CEPA-094-005 | RN-6 |
| CEPA-094 | TC | TC-094-04 | Generar sin período → error de validación. | TC-CEPA-094-006 | RN-2 |
| CEPA-094 | PLANILLA | Hoja de licencias (planilla CEPA) | El epic reemplaza la generación manual de indicadores desde las 7 planillas; el acumulado debe reproducir la hoja de licencias. | TC-CEPA-094-007 | RN-1, RN-3 |
| CEPA-095 | AC | CA-1 | Dado que consulta adherencia, cuando selecciona un recorte, entonces muestra % adherencia = citas realizadas / citas agendadas. | TC-CEPA-095-001 | RN-1, RN-6 |
| CEPA-095 | AC | CA-2 | Dado que consulta el avance, cuando selecciona un caso/plan, entonces muestra etapa, sesiones restantes, % por plan y aumentos ISL. | TC-CEPA-095-002 | RN-2 |
| CEPA-095 | AC | CA-3 | Dado que consulta estadísticas de fármacos, cuando filtra por tratamiento/programa/profesional, entonces muestra las estadísticas del recorte (D7). | TC-CEPA-095-003 | RN-3 |
| CEPA-095 | AC | CA-4 | Dado que una métrica se publica, cuando pasa el control de calidad, entonces cuenta con validación de resultado y de proceso y responsable asignado (D5). | TC-CEPA-095-004 | RN-4, RN-6 |
| CEPA-095 | BR | RN-5 | RBAC — Coordinación explota estas métricas; Auditor solo lectura; el perfil Clínico no existe (D1). | TC-CEPA-095-005 | RN-5 |
| CEPA-095 | TC | TC-095-03 | Paciente con 0 citas agendadas → sin división por cero; estado 'no aplica/sin datos'. | TC-CEPA-095-006 | RN-1 |
| CEPA-096 | AC | CA-1 | Dado que el administrativo abre la ventana de un proceso, cuando carga, entonces muestra la información consolidada con campos y acciones. | TC-CEPA-096-001 | RN-2, RN-3 |
| CEPA-096 | AC | CA-2 | Dado que está en una ventana de proceso, cuando filtra u ordena, entonces la vista se actualiza al recorte y permite acceder al detalle. | TC-CEPA-096-002 | RN-2 |
| CEPA-096 | AC | CA-3 | Dado que existen las cinco vistas de proceso, cuando el administrativo navega entre ellas, entonces cada una presenta su información específica accionable. | TC-CEPA-096-003 | RN-1, RN-2 |
| CEPA-096 | AC | CA-4 | Dado que el usuario es Auditor, cuando abre la vista de auditoría, entonces accede en solo lectura sin edición de datos clínicos. | TC-CEPA-096-004 | RN-4 |
| CEPA-096 | BR | RN-3 | Las vistas presentan datos en tiempo real desde la fuente única de verdad; no son exports estáticos. | TC-CEPA-096-005 | RN-3 |
| CEPA-096 | BR | RN-5 | El estado completo de un caso/proceso debe ser accesible rápidamente (alineado con OU3, <10 s). | TC-CEPA-096-006 | RN-5 |
| CEPA-096 | TC | TC-096-04 | Abrir vista de un proceso vacío → estado vacío explícito, sin error. | TC-CEPA-096-007 | RN-2 |
| CEPA-097 | AC | CA-1 | Dado que genera el reporte de ODAS vencidas, cuando lo solicita, entonces lista las ODAS con vencimiento anterior a hoy, con folio/paciente y fechas. | TC-CEPA-097-001 | RN-1, RN-2 |
| CEPA-097 | AC | CA-2 | Dado que aplica filtros (período, programa, región/comuna), cuando confirma, entonces el reporte se acota y permite descarga estándar. | TC-CEPA-097-002 | RN-3, RN-4 |
| CEPA-097 | AC | CA-3 | Dado que una ODA aún no ha vencido, cuando se genera el reporte de vencidas, entonces no aparece en el listado. | TC-CEPA-097-003 | RN-1, RN-2 |
| CEPA-097 | BR | RN-5 | RBAC — Administrativo y Coordinación generan; Auditor solo lectura; el perfil Clínico no existe (D1). | TC-CEPA-097-004 | RN-5 |
| CEPA-097 | BR | RN-6 | La generación del reporte queda trazada en el log de auditoría. | TC-CEPA-097-005 | RN-6 |
| CEPA-097 | TC | TC-097-04 | Sin ODAS vencidas → listado vacío explícito, sin error. | TC-CEPA-097-006 | RN-1 |
| CEPA-100 | AC | CA-1 | Dado un control médico dentro de la ventana de aviso, cuando el job se ejecuta, se genera alerta de 'próximo control médico' para el administrativo asignado. | TC-CEPA-100-001 | RN-1, RN-3, RN-5 |
| CEPA-100 | AC | CA-2 | Dado una licencia que vence en 3 días hábiles, cuando el job ejecuta, se genera alerta de 'vencimiento de licencia médica' para el administrativo asignado. | TC-CEPA-100-002 | RN-1, RN-3, RN-5, RN-6 |
| CEPA-100 | AC | CA-3 | Dado un caso EPT con plazo de informe EPT o entrega ISL dentro de la ventana, cuando el job se ejecuta, se genera alerta 'plazo EPT/ISL por vencer'. | TC-CEPA-100-003 | RN-1, RN-3, RN-5, RN-6 |
| CEPA-100 | AC | CA-4 | Dado un caso en inicio de tratamiento sin consentimiento firmado, cuando el job se ejecuta, se genera alerta 'consentimiento informado pendiente'. | TC-CEPA-100-004 | RN-1 |
| CEPA-100 | AC | CA-5 | Dado una receta con fecha de revisión dentro de los próximos 5 días, cuando el job se ejecuta, se genera alerta 'receta por renovar/gestionar'. | TC-CEPA-100-005 | RN-1, RN-3, RN-5 |
| CEPA-100 | AC | CA-6 | Dado una ODA con vencimiento dentro de la ventana de aviso, cuando el job se ejecuta, se genera alerta 'ODA por vencer' (D3). | TC-CEPA-100-006 | RN-1, RN-3, RN-5 |
| CEPA-100 | AC | CA-7 | Dado una alerta activa para un plazo y caso, cuando el job se vuelve a ejecutar, no se crea una alerta duplicada. | TC-CEPA-100-007 | RN-4 |
| CEPA-100 | AC | CA-8 | Dado cualquier plazo perentorio soportado, cuando llega su vencimiento, existe registro de al menos una alerta previa (OU4). | TC-CEPA-100-008 | RN-1, RN-7 |
| CEPA-100 | BR | RN-2 | El job de revisión se ejecuta programado en días hábiles, respetando la ventana de mantenimiento nocturna, con frecuencia configurable (mínimo diaria). | TC-CEPA-100-009 | RN-2 |
| CEPA-100 | BR | RN-3 | Cada tipo de alerta tiene ventana de aviso parametrizable; defaults: licencia 3 días hábiles, receta 5 días. | TC-CEPA-100-010 | RN-3 |
| CEPA-100 | BR | RN-5 | La alerta se dirige al administrativo asignado; Coordinación/Auditor visualizan según alcance; el perfil Clínico no recibe alertas (D1). | TC-CEPA-100-011 | RN-5 |
| CEPA-100 | BR | RN-6 | Cada cálculo de plazo respeta días hábiles cuando el plazo regulatorio así lo define (licencias, EPT/ISL). | TC-CEPA-100-012 | RN-6, RN-3 |
| CEPA-100 | BR | RN-8 | La generación de alertas y su resolución se registran en el log de auditoría (OI1). | TC-CEPA-100-013 | RN-8, RN-7 |
| CEPA-100 | TC | TC-100-04 | Negativo: licencia que vence en 30 días (fuera de ventana) no genera alerta de vencimiento. | TC-CEPA-100-014 | RN-3 |
| CEPA-101 | AC | CA-1 | Dado un usuario con alertas pendientes, cuando inicia sesión, ve el panel de notificaciones con sus alertas activas. | TC-CEPA-101-001 | RN-1, RN-6 |
| CEPA-101 | AC | CA-2 | Dado un administrativo con casos asignados, cuando abre el panel, solo ve alertas de sus casos, no las de otros administrativos. | TC-CEPA-101-002 | RN-2 |
| CEPA-101 | AC | CA-3 | Dado un usuario Coordinación o Auditor, cuando abre el panel, ve alertas según su alcance sin poder editar datos clínicos. | TC-CEPA-101-003 | RN-2, RN-4 |
| CEPA-101 | AC | CA-4 | Dado una alerta visible, cuando el usuario la marca como leída/resuelta, cambia de estado, deja de contar como pendiente y se registra la acción. | TC-CEPA-101-004 | RN-5 |
| CEPA-101 | AC | CA-5 | Dado una alerta del panel, cuando el usuario hace clic en ella, el sistema navega al caso/módulo de origen. | TC-CEPA-101-005 |  |
| CEPA-101 | BR | RN-3 | Perfiles habilitados: Coordinación, Administrativo, Auditor; el perfil Clínico no existe (D1) y no recibe panel. | TC-CEPA-101-006 | RN-3 |
| CEPA-101 | BR | RN-6 | El panel refleja las alertas generadas por CEPA-100; ambas comparten el mismo origen de datos. | TC-CEPA-101-007 | RN-6, RN-1 |
| CEPA-101 | TC | TC-101-05 | Borde: usuario sin alertas pendientes inicia sesión y el panel se muestra vacío / 'sin notificaciones' sin error. | TC-CEPA-101-008 | RN-1 |
| CEPA-102 | AC | CA-1 | Dado una alerta generada para un usuario con correo, cuando el sistema procesa el envío, envía un correo vía SMTP institucional al responsable. | TC-CEPA-102-001 | RN-2, RN-4, RN-6 |
| CEPA-102 | AC | CA-2 | Dado un evento que no es alerta, cuando el sistema evalúa enviar correo, NO se envía (email solo para alertas, D12). | TC-CEPA-102-002 | RN-1 |
| CEPA-102 | AC | CA-3 | Dado SMTP no disponible, cuando el sistema intenta enviar, se degrada de forma controlada (in-app intacta) y el fallo queda registrado (PA6). | TC-CEPA-102-003 | RN-2, RN-3, RN-4 |
| CEPA-102 | AC | CA-4 | Dado un correo de alerta ya enviado, cuando el proceso se vuelve a ejecutar, no se reenvía duplicado. | TC-CEPA-102-004 | RN-4 |
| CEPA-102 | BR | RN-4 | Cada envío (éxito/fallo) se registra para trazabilidad; los fallos no bloquean la generación de alertas. | TC-CEPA-102-005 | RN-4 |
| CEPA-102 | BR | RN-5 | WhatsApp queda fuera de alcance (P2) por ausencia de WABA; la arquitectura soporta canales futuros pero no se implementan en v1. | TC-CEPA-102-006 | RN-5 |
| CEPA-102 | BR | RN-6 | Solo reciben correo los perfiles operativos con correo válido; el perfil Clínico no aplica (D1). | TC-CEPA-102-007 | RN-6, RN-3 |
| CEPA-103 | AC | CA-1 | Dado un usuario con tareas pendientes asignadas a su rol, cuando accede a su sección de tareas, ve la lista que le corresponde según perfil y asignación. | TC-CEPA-103-001 | RN-1, RN-2 |
| CEPA-103 | AC | CA-2 | Dado una tarea pendiente, cuando el usuario la marca como completada, cambia de estado, sale de pendientes y se registra quién y cuándo. | TC-CEPA-103-002 | RN-3 |
| CEPA-103 | AC | CA-3 | Dado dos usuarios con tareas distintas, cuando cada uno abre su lista, cada uno ve solo sus tareas. | TC-CEPA-103-003 | RN-1, RN-2 |
| CEPA-103 | AC | CA-4 | Dado un usuario de Coordinación, cuando abre tareas pendientes, puede ver el estado de tareas del equipo según su alcance de supervisión. | TC-CEPA-103-004 | RN-2, RN-5 |
| CEPA-103 | BR | RN-2 | Perfiles aplicables: Administrativo (operación) y Coordinación (supervisión); el perfil Clínico no existe (D1). | TC-CEPA-103-005 | RN-2 |
| CEPA-103 | BR | RN-4 | Las tareas se originan de procesos operativos y conviven con las alertas del motor (CEPA-100) sin duplicar su semántica de plazo. | TC-CEPA-103-006 | RN-4 |
| CEPA-103 | TC | TC-103-05 | Borde: usuario sin tareas pendientes abre la lista y esta se muestra vacía sin error. | TC-CEPA-103-007 |  |
| CEPA-110 | AC | CA-1 | Dado el editor de formularios, cuando la coordinadora agrega un campo nuevo y publica, entonces el campo aparece en el formulario operativo sin despliegue de código. | TC-CEPA-110-001 | RN-2, RN-5 |
| CEPA-110 | AC | CA-2 | Dado un campo no obligatorio, cuando la coordinadora lo elimina/desactiva y publica, entonces deja de mostrarse en nuevas capturas y los datos históricos se conservan. | TC-CEPA-110-002 | RN-2, RN-3 |
| CEPA-110 | AC | CA-3 | Dado un formulario configurado, cuando la coordinadora guarda cambios como borrador, entonces no afectan producción hasta publicar la nueva versión. | TC-CEPA-110-003 | RN-2 |
| CEPA-110 | AC | CA-4 | Dado un usuario sin perfil Coordinación, cuando intenta acceder al editor de formularios, entonces el sistema deniega el acceso (RBAC EPIC-00). | TC-CEPA-110-004 | RN-1 |
| CEPA-110 | BR | RN-2 | Cada cambio publicado genera una nueva versión del formulario; las capturas previas mantienen la versión con que se crearon. | TC-CEPA-110-005 | RN-2, RN-3 |
| CEPA-110 | BR | RN-4 | Todo cambio de configuración (alta/baja/modificación de campo, publicación) se registra en el log de auditoría de EPIC-00 (quién, qué, cuándo). | TC-CEPA-110-006 | RN-4 |
| CEPA-110 | BR | RN-5 | No se permite publicar un formulario que no pase la validación de parametrización (CEPA-111, RN-1). | TC-CEPA-110-007 | RN-5 |
| CEPA-110 | TC | TC-110-06 | Usuario Auditor autenticado intenta publicar cambios en un formulario; acceso denegado (Auditor es solo lectura). | TC-CEPA-110-008 | RN-1 |
| CEPA-111 | AC | CA-1 | Dado un intento de publicación, cuando la validación detecta campo sin tipo/nomenclatura inválida/configuración inconsistente, entonces bloquea la publicación y lista los errores. | TC-CEPA-111-001 | RN-1, RN-5 |
| CEPA-111 | AC | CA-2 | Dado un formulario con un campo obligatorio del sistema, cuando la coordinadora intenta quitarlo o desactivarlo, entonces el sistema impide la acción e informa que no es removible. | TC-CEPA-111-002 | RN-2, RN-5 |
| CEPA-111 | AC | CA-3 | Dado un formulario con campos obligatorios presentes y bien parametrizados, cuando la coordinadora publica, entonces la publicación se completa y queda marcado como válido. | TC-CEPA-111-003 | RN-1, RN-3, RN-5 |
| CEPA-111 | AC | CA-4 | Dado un campo obligatorio de dominio cerrado, cuando un administrativo guarda dejándolo vacío, entonces el sistema rechaza el guardado e indica el campo faltante. | TC-CEPA-111-004 | RN-4 |
| CEPA-111 | BR | RN-3 | Los campos obligatorios usan nomenclatura estandarizada (identificador y dominio controlado) para que la información sea comparable entre módulos y reportes. | TC-CEPA-111-005 | RN-3 |
| CEPA-111 | BR | RN-4 | Los campos de dominio cerrado solo aceptan valores del catálogo definido; los obligatorios no admiten valor vacío. | TC-CEPA-111-006 | RN-4 |
| CEPA-111 | BR | RN-5 | Cada intento de publicación (exitoso o bloqueado) y cada intento de remoción de campo obligatorio se registran en el log de auditoría de EPIC-00. | TC-CEPA-111-007 | RN-5 |
| CEPA-111 | TC | TC-111-06 | Usuario Administrativo intenta modificar la parametrización de campos obligatorios; acceso denegado por RBAC EPIC-00 (solo Coordinación). | TC-CEPA-111-008 |  |
| CEPA-112 | AC | CA-1 | Dado un PDF legible con datos sociodemográficos, cuando el sistema lo procesa, entonces muestra los campos extraídos pre-llenados para revisión. | TC-CEPA-112-001 | RN-1 |
| CEPA-112 | AC | CA-2 | Dado un PDF con datos pre-llenados, cuando el administrativo corrige valores y confirma, entonces se guardan los datos editados (la edición humana prevalece). | TC-CEPA-112-002 | RN-1, RN-4 |
| CEPA-112 | AC | CA-3 | Dado un archivo no PDF o PDF ilegible, cuando el administrativo intenta cargarlo, entonces el sistema informa que no pudo extraer datos y permite la captura manual. | TC-CEPA-112-003 | RN-3 |
| CEPA-112 | AC | CA-4 | Dado un usuario sin permiso de captura sobre el módulo destino, cuando intenta cargar un PDF para extracción, entonces el sistema deniega la acción (RBAC EPIC-00). | TC-CEPA-112-004 |  |
| CEPA-112 | BR | RN-2 | El aplicativo no escribe sobre SALUTEM/SAM (D12); la lectura de PDF alimenta únicamente los módulos del Sistema CEPA. | TC-CEPA-112-005 | RN-2 |
| CEPA-112 | BR | RN-3 | Si la extracción falla o el PDF es ilegible, el sistema degrada con gracia a captura manual sin perder el documento cargado. | TC-CEPA-112-006 | RN-3 |
| CEPA-112 | BR | RN-4 | Los datos confirmados se validan contra las reglas de campos obligatorios y dominios (CEPA-111) antes de guardar. | TC-CEPA-112-007 | RN-4 |
| CEPA-112 | BR | RN-5 | La carga del documento y el guardado de los datos extraídos/editados se registran en el log de auditoría de EPIC-00. | TC-CEPA-112-008 | RN-5 |
| CEPA-120 | AC | CA-1 | Dado cliente con JWT válido, cuando invoca /api/v1 con JSON, entonces responde 200/201 con JSON conforme al contrato. | TC-CEPA-120-001 | RN-1, RN-2, RN-3 |
| CEPA-120 | AC | CA-2 | Dado cliente sin token o con JWT inválido/expirado, cuando invoca endpoint protegido, entonces 401 con JSON de error sin datos del recurso. | TC-CEPA-120-002 | RN-2, RN-3 |
| CEPA-120 | AC | CA-3 | Dado documentación automática, cuando se accede a Swagger/OpenAPI, entonces se listan el 100% de los endpoints con esquemas, errores y auth. | TC-CEPA-120-003 | RN-5 |
| CEPA-120 | AC | CA-4 | Dado cliente que supera el límite por ventana, cuando envía una solicitud adicional, entonces 429 con tiempo de reintento. | TC-CEPA-120-004 | RN-4, RN-3 |
| CEPA-120 | AC | CA-5 | Dado v1 publicada, cuando se publica v2 con cambios incompatibles, entonces v1 sigue operativa y los clientes no se rompen. | TC-CEPA-120-005 | RN-1 |
| CEPA-120 | BR | RN-3 | Request/response en JSON; errores con códigos HTTP estándar y cuerpo JSON uniforme. | TC-CEPA-120-006 | RN-3 |
| CEPA-120 | BR | RN-6 | Toda operación de integración que crea o modifica datos queda en el log de auditoría (quién/qué/cuándo). | TC-CEPA-120-007 | RN-6, RN-2 |
| CEPA-121 | AC | CA-1 | Dado cliente autenticado, cuando busca paciente por RUT/nombre/folio, entonces devuelve datos o 404, y permite CRUD según permisos. | TC-CEPA-121-001 | RN-3, RN-6 |
| CEPA-121 | AC | CA-2 | Dado un ingreso existente, cuando el cliente consulta o actualiza su estado, entonces la API refleja el estado y persiste con trazabilidad. | TC-CEPA-121-002 | RN-4, RN-7 |
| CEPA-121 | AC | CA-3 | Dado sistema externo integrado, cuando envía (push) o solicita (pull) datos clínicos, entonces la API procesa ambos sentidos confirmando con HTTP estándar. | TC-CEPA-121-003 | RN-1, RN-7 |
| CEPA-121 | AC | CA-4 | Dado paciente con licencias, cuando consulta el recurso de licencias, entonces devuelve historial y total de días acumulados del folio. | TC-CEPA-121-004 | RN-5 |
| CEPA-121 | AC | CA-5 | Dado el intercambio bidireccional, cuando CEPA procesa datos de SAM/SALUTEM, entonces no escribe sobre SALUTEM y persiste en el dominio CEPA. | TC-CEPA-121-005 | RN-1, RN-2 |
| CEPA-121 | BR | RN-3 | Pacientes soporta CRUD y búsqueda por RUT (con validación de DV), nombre y folio. | TC-CEPA-121-006 | RN-3 |
| CEPA-121 | BR | RN-6 | Solo se exponen los recursos definidos en §8.2; no se inventan endpoints adicionales. | TC-CEPA-121-007 | RN-6, RN-4 |
| CEPA-121 | BR | RN-7 | Toda operación de escritura/recepción se registra en el log de auditoría (consistente con OI1 y RBAC). | TC-CEPA-121-008 | RN-7 |
| CEPA-121 | TC | TC-121-06 | Intentar actualizar estado de un Ingreso con token sin permiso → 403 Forbidden, sin cambios en el ingreso. | TC-CEPA-121-009 | RN-4, RN-7 |
| CEPA-122 | AC | CA-1 | Dado cliente IMED autenticado, cuando envía una licencia médica electrónica, entonces CEPA la persiste vinculada al paciente/folio y confirma con HTTP estándar. | TC-CEPA-122-001 | RN-1, RN-3 |
| CEPA-122 | AC | CA-2 | Dado cliente IMED autenticado, cuando envía una receta electrónica, entonces CEPA la persiste vinculada al folio del paciente. | TC-CEPA-122-002 | RN-1, RN-3 |
| CEPA-122 | AC | CA-3 | Dado que IMED es P2 y depende de PA5, cuando se difiere, entonces la arquitectura permite habilitarla a futuro sin rediseño del contrato v1. | TC-CEPA-122-003 | RN-2, RN-4 |
| CEPA-122 | BR | RN-3 | Los datos recibidos desde IMED se vinculan al folio del paciente y se registran en el log de auditoría. | TC-CEPA-122-004 | RN-3, RN-1 |
| CEPA-122 | BR | RN-4 | IMED reutiliza los principios de §8.1 (versionado, JWT, JSON, rate limiting); no introduce un contrato paralelo. | TC-CEPA-122-005 | RN-4 |
| CEPA-122 | TC | TC-122-03 | Enviar licencia IMED sin campos obligatorios → 422 Unprocessable Entity; nada se persiste. | TC-CEPA-122-006 | RN-1 |
| CEPA-122 | TC | TC-122-04 | Enviar receta con token no autorizado para IMED → 403 Forbidden. | TC-CEPA-122-007 | RN-1 |