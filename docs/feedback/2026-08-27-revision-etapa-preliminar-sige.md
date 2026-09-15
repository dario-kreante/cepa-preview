# Revisión etapa preliminar SIGE-CEPA — ambiente de prueba

Fuente: correo de María del Pilar García Zerene (mgarciaz@utalca.cl), 27-08-2026,
hilo "RE: Observaciones del ambiente de pruebas: ¿te sirve el viernes 4?".
Adjunto original: `Revision-etapa-preliminar-SIGE.docx`.

Pendientes que Pilar anunció en el mismo correo:
- Detalles de la ficha (los enviaría la semana siguiente).
- Hay pacientes de prueba con atenciones simuladas disponibles; puede generar más si se necesita.

## Nuevo ingreso
- Folio: permitir incorporarlo de forma manual, ya que cada programa maneja sus folios internos. Incluir las reglas del folio.
- Incorporar fecha de ingreso y tipo de ingreso (desplegable: DIEP, DIAT, DIEP sin EPT, Reingreso FUPM, Reingreso SUSESO, Reingreso ISL, Derivación otro prestador, Flujo PAPT, Convenio, Consulta espontánea, Proyecto).
- No fue posible editar la ficha posteriormente.
- Incluir un apartado "Fármacos ingreso" SI/NO.
- En el resumen de controles (apartado a la derecha): ¿se verá lo que aparece en ficha o hay que dejar un comentario manual?

## Licencias médicas
- Incluir filtro por médico, fecha de emisión/vencimiento (rango), RUT, nombre usuario(a).
- ¿Cómo se generan las alertas automáticas? Definir la regla específicamente: días de vencimiento y reposo parcial, mensaje para usuario administrativo.
- Los ítems de inicio y término de licencia están repetidos.
- Al ingresar nueva licencia médica, agregar GAF. Alerta por GAF: definir regla.
- ¿A qué se refiere "ingreso ID"? ¿RUT, folio, nombre?

## Fármacos
- ¿Cómo se generan las alertas? Crear reglas.
- Incluir un apartado "Fármacos ingreso" SI/NO y luego especificar.

## Controles médicos
- En el apartado RECAS, incluir en desplegable: EP, EC, AT, AC, NPE, No aplica.
- No se pudo usar el desplegable hacia abajo.
- El GAF es un nivel entre dos valores porcentuales, por ejemplo 11-20%.
- No se guardaron las actualizaciones manuales.

## EPT
- En la carga del caso, preferentemente vincularlo con folio.
- ¿Cómo se realiza la carga de los casos de EPT? ¿Puede ser carga manual? Enviar Excel.

## Reintegro
- No fue posible cargar nuevo caso.
- Generar alerta en "Remitido a ISL". Incluir regla.
- No fue posible editar la RECA.

## Auditoría
- ¿Es posible agregar más apartados para filtros? P. ej. convenio, tipo de ingreso, mes/año de ingreso, estado, profesional. Registrar campos.

## Agendamiento
- ¿El módulo de agendamiento puede vincularse con la agenda de SALUTEM?

## Reportería
- ¿Se puede generar un indicador de adherencia general? P. ej. por profesional, por convenio, por tipo de ingreso. Registrar campos. Agregar ejemplo de referencia.
