# Mantenedor de convenios espejo de SALUTEM — diseño

Fecha: 2026-11-23 · Origen: pregunta de Pilar (WhatsApp, 20-11-2026)

## Intención

La Unidad Clínica suma convenios con frecuencia (hoy Colegio Inglés, Rangers…). Pilar
preguntó si, ya en producción, un convenio nuevo se puede agregar a mano. Hoy no se puede:
las listas de programa y de tipo de derivación están fijas en el código, y el campo
`Ingreso.tipo_convenio` existe pero ningún formulario lo llena.

El CEPA registra cada convenio en SALUTEM de todos modos. Por eso SIGE toma la lista de
SALUTEM y precarga el convenio de cada paciente: el CEPA lo carga una sola vez, en SALUTEM.

## Lo que ya hay en SALUTEM (revisado en QA el 23-11-2026, solo lectura)

- `GET /financiadores` (sin parámetros) devuelve `{id, nombre, tipo, activo}`. En QA hay
  26 entradas: 23 de `tipo = "CONVENIO"` (entre ellas «Convenio Colegio Inglés», ISL por
  región, «Convenio SSM», «Derivación espontánea», «Programa Intervención Psicologíca
  Temprana», «Proyecto Fondecyt» y «Sin Convenio»; una inactiva) y 3 de
  `tipo = "FINANCIADOR"` (CONVENIO ISL, PARTICULAR y FONASA).
- `persona.origen` trae el convenio del paciente como texto («Convenio ISL Maule»,
  «Sin Origen»). SIGE ya lo guarda en `salutem_persona.contenido` y no lo usa.
- Las mayúsculas no coinciden entre `origen` y el catálogo («Maule» / «MAULE»). Hay nombres
  de más de 40 caracteres.
- `persona.financiador` y `cita.financiadorNombre` indican quién paga, no el convenio.
  Quedan fuera.
- QA es un ambiente de capacitación (8 personas). Los nombres se revalidan en producción.

## Metas

1. Una lista de convenios en SIGE que se mantiene sola desde SALUTEM.
2. En Configuración, una pantalla «Convenios» para verla, actualizarla al momento, ocultar
   convenios y agregar uno que solo exista en SIGE.
3. En el alta y la edición del ingreso, un selector «Convenio» precargado desde el `origen`
   del paciente en SALUTEM, que se puede corregir.
4. Los reportes que ya usan `tipo_convenio` (dashboard, reporte de ingresos, reporte
   Convenio) empiezan a mostrar datos sin cambiar su lógica.

## No metas

- No cambia **Programa** (Regular, Ley Karin, PIPT) ni **Tipo de derivación**. Decisión de
  Darío (23-11): el convenio es un dato aparte del programa.
- No se escribe en SALUTEM.
- No se usa `financiador` (quién paga).
- No se rellenan ingresos antiguos con el `origen` de SALUTEM (ver Pendientes).

## Anti-metas

- Que el CEPA tenga que cargar el mismo convenio dos veces (en SALUTEM y en SIGE).
- Que un convenio desactivado u ocultado borre el valor de un ingreso ya guardado, o que
  un renombre lo cambie sin dejar rastro en la auditoría.
- Que la precarga ponga un convenio equivocado sin que se note: si el `origen` no calza con
  ningún convenio, el selector queda vacío, nunca adivina.

## Enfoques considerados

- **A. Espejo de SALUTEM (elegido).** Catálogo sincronizado desde `GET /financiadores`,
  precarga desde `persona.origen`, más altas manuales en SIGE. Un solo lugar donde el CEPA
  registra el convenio.
- **B. Mantenedor manual con precarga por nombre.** Más simple, pero exige cargar todo dos
  veces, y si el nombre no coincide la precarga falla sin avisar.
- **C. Leer `origen` directo, sin mantenedor.** Descartado: no deja al CEPA administrar la
  lista, que es lo que se pidió.

## Diseño

### Datos

Tabla nueva `convenio`:

| columna | tipo | nota |
|---|---|---|
| `id` | BigInteger PK | |
| `nombre` | String(120), not null | se muestra tal cual viene de SALUTEM |
| `nombre_normalizado` | String(120), único | clave de comparación (sin tildes, minúsculas, espacios colapsados; igual que `normalizar_nombre` de profesionales) |
| `salutem_id` | BigInteger, único, nullable | null = creado en SIGE |
| `activo_salutem` | Boolean | lo que dice SALUTEM |
| `visible` | Boolean, default true | lo decide el CEPA en SIGE; SALUTEM no lo toca |
| `sincronizado_en` | DateTime tz, nullable | |
| `created_at` / `updated_at` | DateTime tz | |

Un convenio aparece en el selector si `visible` y (`salutem_id` es null o `activo_salutem`).

`Ingreso.tipo_convenio` pasa de String(40) a String(120) y **sigue guardando el nombre
como texto**: así los reportes existentes funcionan sin cambios, y un convenio que después
se oculta o desactiva no altera los ingresos ya guardados.

Migración nueva: revisar `origin/main` y `alembic heads` antes de numerar (la última en
main es 1490). Debe funcionar en Oracle y en Postgres de test.

### Sincronización del catálogo

- Cliente SALUTEM: método `obtener_financiadores()` que llama `GET /financiadores` y
  devuelve los de `tipo == "CONVENIO"`. El stub de tests devuelve una lista fija.
- Servicio `sincronizar_convenios(db, ahora)`:
  - empareja por `salutem_id`; si no hay, adopta un convenio manual con el mismo
    `nombre_normalizado` (le asigna el `salutem_id`);
  - crea los nuevos, actualiza `nombre` y `activo_salutem`, y nunca toca `visible`;
  - si SALUTEM renombra un convenio, también actualiza `Ingreso.tipo_convenio` de los
    ingresos con el nombre anterior, para que los reportes no partan el convenio en dos
    *(decisión del diseño)*. Se registra **un** evento de auditoría por convenio
    renombrado: nombre anterior, nombre nuevo y cantidad de ingresos actualizados. No se
    audita cada ingreso por separado. Esto no es un cambio «silencioso»: queda auditado y
    no cambia el significado del dato;
  - si el nombre nuevo choca con el `nombre_normalizado` de otro convenio (por ejemplo, uno
    manual), ese convenio no se actualiza en esta pasada y el choque se informa en
    `errores`. El resto del sync sigue;
  - «Sin Convenio» (tipo CONVENIO en SALUTEM) se sincroniza, pero nace con
    `visible = false`: equivale a la opción «Sin convenio» (= null) del selector, y
    mostrarla partiría ese concepto en dos filas en los reportes *(decisión del diseño)*;
  - nunca borra: lo que deja de venir queda con `activo_salutem = false`;
  - audita las altas y los cambios con el mismo actor que usa el sync.
- Corre en el modo **frío** del orquestador (una vez al día), en su propio `try`, como
  profesionales: si falla, no tumba el resto del sync.
- `POST /api/v1/convenios/actualizar-salutem` lo corre al momento y devuelve
  `{creados, actualizados, desactivados, errores}`.

### API (`/api/v1/convenios`)

Mismos roles que Profesionales: leen Coordinación, Administrativo y Auditor; escriben
Coordinación y Administrativo. El selector del ingreso necesita leer la lista: el `GET`
también lo pueden usar los roles que crean o editan ingresos.

- `GET ""`: lista; `?solo_seleccionables=true` para el selector.
- `POST ""`: alta manual `{nombre}`. Rechaza si ya existe el `nombre_normalizado`.
- `PATCH "/{id}"`: `{visible}`; `{nombre}` solo para los manuales (los de SALUTEM se
  renombran en SALUTEM).
- `POST "/actualizar-salutem"`.
- `GET "/sugerido?paciente_id=…"` o `GET "/sugerido?rut=…"` *(decisión del diseño: la
  precarga sirve tanto al completar un borrador como en un alta nueva)*. Con
  `paciente_id`, busca la `salutem_persona` por `Paciente.salutem_persona_id` y, si no lo
  tiene, por RUT. Así funciona también con los borradores sin RUT. Con `rut` (alta nueva),
  busca por RUT normalizado. Lee `contenido.origen` y devuelve el convenio seleccionable
  cuyo `nombre_normalizado` coincide, o `null`. Dan `null` «Sin Origen», «Sin Convenio» y
  un origen sin pareja. El frontend pide la sugerencia con `paciente_id` cuando viene de un
  borrador, y con `rut` cuando el RUT escrito es válido.

### Pantalla «Convenios» (Configuración)

Ítem nuevo en la sección Administración del menú y en el índice de Configuración, al estilo
de Profesionales:

```
Convenios                                   [Actualizar desde SALUTEM] [+ Agregar]
Última actualización: 23-11-2026 07:10
┌────────────────────────────────────┬──────────┬─────────────┬─────────┐
│ Nombre                             │ Origen   │ En SALUTEM  │ Visible │
├────────────────────────────────────┼──────────┼─────────────┼─────────┤
│ Convenio Colegio Inglés            │ SALUTEM  │ Activo      │  [x]    │
│ Convenio ISL MAULE                 │ SALUTEM  │ Activo      │  [x]    │
│ Proyecto ISL Biobío                │ SALUTEM  │ Inactivo    │  [ ]    │
│ Convenio Rangers                   │ SIGE     │ —           │  [x]    │
└────────────────────────────────────┴──────────┴─────────────┴─────────┘
```

Un convenio manual muestra un aviso de que conviene crearlo también en SALUTEM. Al
crearlo allá, el siguiente sync lo adopta por nombre.

### Ficha de ingreso

- `AltaIngresoPage` y `EditarFichaDialog`: selector opcional «Convenio», siempre visible
  (el catálogo incluye convenios ISL, «Derivación espontánea», etc., así que no depende del
  tipo de derivación). Primera opción: «Sin convenio» (= null).
- En el alta, si `GET /convenios/sugerido` devuelve un convenio, se preselecciona con una
  nota breve «Sugerido desde SALUTEM». No pisa un valor que el usuario ya eligió.
- En la edición, un valor guardado que ya no es seleccionable se muestra igual y se
  conserva al guardar, como hace `opcionesPrograma` con los programas antiguos.
- Validación en el backend: el valor nuevo debe ser el nombre de un convenio seleccionable,
  o el mismo que ya tenía el ingreso.

### Reporte Convenio

El campo de texto libre «Tipo convenio» de la pestaña Convenio (`ReportesPage`) pasa a ser
un selector con todos los convenios del catálogo, incluidos los ocultos e inactivos, porque
se puede reportar un período pasado. También suma los valores distintos de
`ingreso.tipo_convenio` que no estén en el catálogo (por ejemplo «ISL» o «Particular»,
que vienen de datos anteriores), para que sigan siendo consultables *(decisión del
diseño)*.

### Detalles del backend que hoy faltan

- `IngresoUpdate` no incluye `tipo_convenio`: hay que agregarlo, con la misma validación
  que el alta.

## Pendientes del builder

- Los nombres y el orden exacto de los componentes, y el texto de los avisos.
- Tests: servicio de sincronización (alta, renombre con arrastre a ingresos, desactivación,
  adopción por nombre, `visible` respetado), sugerencia (coincidencia sin mayúsculas ni
  tildes, «Sin Origen», paciente sin persona en SALUTEM), validación del ingreso y el
  selector en el frontend con MSW.

## Pendientes con el CEPA (no bloquean)

- Confirmar con Pilar que crean los convenios nuevos en SALUTEM como «Convenio» (así
  aparece Colegio Inglés en QA) y que `origen` es donde se asigna el del paciente.
- Si quieren rellenar los ingresos ya existentes con el `origen` de SALUTEM. Hoy queda
  fuera: en QA los valores de `tipo_convenio` vienen de los datos de prueba.
