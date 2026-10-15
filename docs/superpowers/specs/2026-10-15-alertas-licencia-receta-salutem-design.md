# Diseño — Alertas de licencia y receta desde los controles de SALUTEM, con los archivos de la biblioteca

> **Estado:** diseño acordado en conversación el 2026-10-15; pendiente de revisión de esta spec.
> **Alcance:** solo lectura sobre SALUTEM (respeta v4 D12). Amplía el sync de SALUTEM (fase 1),
> el motor de alertas (`alerta_notif`, EPIC-10) y la pantalla de Controles.

## Objetivo

Cuando el médico emite una licencia o una receta en un control, la encargada (rol Administrativo)
debe enterarse sin buscarlo: le llega una alerta que dice "este control tiene una licencia" o
"este control tiene una receta", y desde ahí puede abrir los documentos que el médico subió a la
biblioteca de SALUTEM. La alerta no registra nada: la encargada sigue revisando y registrando la
licencia o la receta en el CEPA, como hoy.

**Éxito:** cada control nuevo con licencia o receta produce una sola alerta por tipo, a los ~5 min
de que el sync trae la atención, y la encargada puede abrir el PDF o la foto desde el CEPA.

## Lo que sabemos de SALUTEM (spike del 2026-10-15)

Verificado contra la doc v2.1 (Notion "API SALUTEM DOC") y contra SALUTEM QA, empresa 96, con el
paciente de prueba de Pilar (`persona_id` 1180505), al que ella subió un archivo por la sección
de licencias y otro por la de recetas.

| Hallazgo | Consecuencia |
|---|---|
| El médico siempre completa el formulario: "Indicación de reposo"/"Tipo de reposo" en el control, y las recetas como indicación (`tipo` "Receta Medicamentos" o "Receta") o en el campo "Indicaciones" | **La alerta se dispara por el formulario**, que ya leemos y está unido a la cita |
| Las indicaciones de `tipo` "Documento" son el certificado de reposo que genera SALUTEM ("…debe permanecer en reposo desde el … hasta el …") | Señal adicional de licencia, también unida a la cita |
| `GET /personas-archivos {persona_id}` lista la biblioteca: `id`, `nombre`, `nombreOriginal`, `fechaCreacion` (`DD-MM-AAAA HH:MM`), `tipo` ("documento", "imagen"), `descripcion` | Se puede listar en una llamada por persona |
| `GET /personas-archivos {persona_id, archivo_id}` devuelve además `archivo_base64` | **La descarga funciona** (PDF de 200 KB y 67 KB). Los archivos antiguos de QA vienen vacíos: esa copia no conserva binarios viejos |
| El listado **no** trae carpeta ni cita, y no filtra por `directorio` (probado 1..60). Los dos archivos de Pilar llegan idénticos salvo el nombre original | **No se puede saber si un archivo es licencia o receta.** No se clasifica |
| La fecha de creación del archivo coincide con el día de la atención (o pocos días después) | Los archivos se unen al control **por fecha** |
| `/personas-archivos-cuenta` vale 0 en todos los pacientes revisados; `/personas-examen` sí trae `citaId`, pero el CEPA no lo usa para estos documentos | Ninguno de los dos se usa |

## Decisiones

1. **La alerta sale del formulario, no de los archivos.** Es la única señal confiable y unida a
   la cita. Un archivo solo no genera alerta (el médico siempre llena el formulario).
2. **Los archivos acompañan a la alerta, sin clasificarse.** Se muestran todos los archivos
   subidos desde el día del control hasta el día anterior al control siguiente (tope 7 días). La
   encargada distingue cuál es cuál al abrirlos. Si el control tiene licencia o receta y no hay
   archivos, se muestra "Sin documentos en la biblioteca".
3. **El CEPA no guarda los archivos.** Guarda solo sus datos (id, nombre, fecha, tipo). "Ver" pide
   el archivo a SALUTEM en ese momento a través del backend y se lo entrega al navegador sin
   escribirlo a disco. Así no se suma almacenamiento de datos de salud (ver COMP-2609-31).
4. **Las alertas se crean en el sync**, no en el job diario de las 07:00: llegan con el retraso
   del sync (~5 min).
5. **Sin avalancha al desplegar.** La vinculación solo vuelve a pasar por un control cuando su
   atención cambia en SALUTEM (`hash_vinculado` ≠ `hash_contenido`). Los controles que ya existen
   y no cambian no generan alertas.

## Componentes

### 1. Señales del formulario — `app/integrations/salutem/senales.py` (nuevo)

Funciones puras sobre el `contenido` de una atención, reutilizando los extractores existentes:

- `tiene_licencia(contenido, fecha) -> bool`: la mención de licencia que ya calcula
  `controles._licencia` (indicaciones + campo "Indicación de reposo"), **más** las indicaciones
  de `tipo` "Documento" cuyo texto, sin HTML, menciona reposo con el extractor de licencias.
  `controles._licencia` pasa a leer también esas indicaciones, para que `tiene_licencia` del
  control y la alerta digan lo mismo.
- `tiene_receta(contenido) -> bool`: hay al menos un fármaco extraído (`extraer_farmacos`) de los
  registros que hoy elige `farmacos_sugeridos._recetas` (indicaciones con "receta" en el `tipo` y
  el campo "Indicaciones"). `_recetas` y `_es_receta` se mueven a este módulo y
  `farmacos_sugeridos` los importa desde aquí.

### 2. Alertas — motor existente (`alerta_notif`)

- `TipoAlerta` suma `LICENCIA_EN_CONTROL = "licencia_en_control"` y
  `RECETA_EN_CONTROL = "receta_en_control"`.
- Cada alerta: `caso_tipo = "control_medico"`, `caso_id = control.id`,
  `plazo_objetivo = fecha_control` (medianoche UTC), `ventana_dias = 0`,
  `usuario_id = _resolver_usuario(ingreso_id)` (mismo destinatario que las demás alertas del
  ingreso), `estado = pendiente`.
- **Dónde:** `app/services/salutem_sync/alertas_control.py` (nuevo), llamado al final de
  `sincronizar_control` cuando el control se crea o se actualiza:
  - Si la señal está presente y el tipo está activo en `config_alerta`, y **no existe ninguna
    alerta** de ese tipo para ese control (en cualquier estado), la crea y registra auditoría
    (`actor = salutem-sync`).
  - Una alerta por control y tipo para siempre: si el médico corrige la atención, no se repite; si
    la encargada ya la resolvió, no reaparece.
- Al eliminar un control desde el sync (atención anulada o que deja de ser control), sus alertas
  `pendiente`/`leida` de estos dos tipos pasan a `resuelta`.
- `VENTANAS_DEFAULT` suma los dos tipos con `{"dias": 0, "habiles": False, "activo": True}`; el
  job diario no construye hitos para ellos. `/config-alertas` los muestra con las etiquetas
  "Licencia emitida en control" y "Receta emitida en control" (solo encender/apagar; los días no
  aplican).
- Correo: sin cambios. Los correos de alertas se envían solo con el endpoint manual existente.

### 3. Copia de la biblioteca — tabla `salutem_archivo` (nueva)

| Columna | Tipo | Nota |
|---|---|---|
| `archivo_id` | BigInteger PK | `id` de SALUTEM |
| `persona_id` | BigInteger, índice | sin FK (como `salutem_cita`) |
| `nombre` | String(255) | `nombreOriginal`, o `nombre` si falta |
| `tipo` | String(30) | "documento", "imagen"… |
| `fecha_creacion` | DateTime, índice | parseada desde `DD-MM-AAAA HH:MM`, hora de Chile |
| `visto_ultima_vez` | DateTime(tz) | |
| `desaparecido_en` | DateTime(tz), nullable | el archivo ya no está en el listado |

Migración Alembic portable (D15: identificadores ≤ 30, tipos genéricos), probada en Oracle.

**Cliente SALUTEM** (`protocol`, stub y HTTP; solo GET, D12):
`listar_archivos(salutem_id) -> list[ArchivoSalutem]` y
`obtener_archivo(salutem_id, archivo_id) -> ContenidoArchivo | None` (bytes decodificados + tipo
MIME detectado por los primeros bytes: pdf, jpeg, png, heic; si no se reconoce,
`application/octet-stream`). Un `archivo_base64` vacío se trata como "sin contenido" y no como
error.

**Cuándo se lista** (`app/services/salutem_sync/archivos.py`, nuevo):
- En cada ciclo `caliente`, para cada persona con un control de los **últimos 7 días**. Cubre los
  archivos subidos después de que el sync trajo la atención (lo normal: el médico los sube al
  final del día o días después).
- Al crear un control desde el sync, para esa persona.
- Upsert por `archivo_id`; los que ya no aparecen quedan con `desaparecido_en`. Un error de
  SALUTEM en una persona se registra en la bitácora y no detiene el ciclo (mismo criterio que el
  resto del sync).

**Unión con el control** (consulta, sin FK): los archivos de la persona del control con
`desaparecido_en IS NULL` y `fecha_creacion` en `[fecha_control, min(fecha del siguiente control
del ingreso, fecha_control + 7 días))`.

### 4. API

- `GET /api/v1/controles/{control_id}/archivos` → `[{archivo_id, nombre, tipo, fecha_creacion}]`,
  ordenados por fecha. Mismos permisos que leer el control.
- `GET /api/v1/salutem/archivos/{archivo_id}/contenido` → el archivo con su `Content-Type` y
  `Content-Disposition: inline`. Busca la persona en `salutem_archivo`, pide el archivo a
  SALUTEM y lo responde sin guardarlo. Mismos permisos; registra auditoría (`READ`,
  `salutem_archivo`). Respuestas: 404 si el archivo no está en la copia o SALUTEM no lo tiene, 502
  si SALUTEM no responde, 404 con mensaje "SALUTEM no entregó el contenido" si llega vacío.
- `AlertaRead` no cambia: la UI pide los archivos al control.

### 5. Frontend

- **Panel de alertas** (`AlertsPanel.tsx`): títulos "Licencia emitida en control" y "Receta
  emitida en control". Al hacer clic, navega a `/controles?control={id}`. La pantalla de
  Controles abre ese control (se agrega la lectura de `?control=`, que hoy no existe).
- **Detalle del control** (pantalla Controles): sección "Documentos en SALUTEM" con la lista de
  archivos (nombre, fecha, tipo) y un botón "Ver" que abre el contenido en una pestaña nueva.
  Si el control tiene licencia o receta y la lista está vacía: "Sin documentos en la biblioteca".
- `/config-alertas`: etiquetas de los dos tipos nuevos; sin campo de días.

## Errores y bordes

- SALUTEM caído al listar: el ciclo sigue; los archivos aparecen en el ciclo siguiente.
- Archivo borrado en SALUTEM: deja de mostrarse (`desaparecido_en`).
- Archivo subido más de 7 días después del control: no se une a ese control (tope deliberado
  para no mezclar controles).
- Dos controles el mismo día del mismo ingreso: ambos muestran los mismos archivos; aceptable.
- Formato de fecha distinto al esperado en `fechaCreacion`: el archivo se guarda con
  `fecha_creacion` nula, se registra un aviso y no se une a ningún control.

## Pruebas (TDD)

- `senales`: licencia por "Indicación de reposo", por indicación con mención y por "Documento" de
  reposo; receta por "Receta Medicamentos", por "Receta" y por el campo "Indicaciones"; casos sin
  señal.
- Alertas del sync: control nuevo con licencia → 1 alerta; actualización sin cambio de señal → no
  duplica; alerta resuelta no reaparece; tipo apagado → no crea; control eliminado → alertas
  resueltas; control sin señal → nada.
- Cliente HTTP: listado, archivo con contenido, archivo con base64 vacío, error de SALUTEM; solo
  GET (`test_salutem_no_escribe` cubre los métodos nuevos).
- Archivos del sync: upsert, desaparición, parseo de fecha, ventana de personas de 7 días, error
  por persona que no detiene el ciclo.
- Unión por fecha: mismo día, días siguientes, corte en el control siguiente, tope de 7 días.
- API: permisos, auditoría del contenido, 404/502.
- Frontend: títulos y navegación de las alertas, `?control=` en Controles, lista de documentos,
  "Ver" y el estado vacío.
- Validación manual en QA con el paciente de Pilar (`persona_id` 1180505): sus dos PDF aparecen en
  el control "Médico/a" del 15-10 y se abren con "Ver".

## Fuera de alcance

- Clasificar los archivos como licencia o receta (la API no lo permite; se retoma si el proveedor
  expone la carpeta).
- Marcar un archivo como "esta es la licencia/receta" desde el CEPA (posible segunda etapa).
- Crear la licencia o la receta automáticamente, enviar correo, guardar copias de los archivos y
  escribir en SALUTEM (D12).
