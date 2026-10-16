# Plan — Sincronización de profesionales desde SALUTEM

Fecha: 2026-10-16. Pedido de Pilar (vía Darío): llevar registro de los profesionales,
lo más completo que permita la API de SALUTEM, actualizado periódicamente y vinculado con
el resto del flujo (atenciones, controles, agenda).

## Qué permite SALUTEM (verificado en QA el 16-10-2026)

- **No hay endpoint de profesionales.** `profesionales`, `profesional`, `especialidades` y
  `agenda` responden `FUNCION_NO_DISPONIBLE`.
- Cada cita (`/cita`) y cada atención (`/atencion`) traen `profesionalId` (estable),
  `profesionalNombre`, `especialidadId`, `especialidadNombre`, `sucursalId`, `sucursalNombre`.
  Un mismo profesional atiende varias especialidades (p. ej. 3090 = Médico/a y Evaluación médica).
- Esos datos ya están en la copia local: `salutem_cita.contenido` y `salutem_atencion.contenido`.

Por eso el catálogo se arma **desde la copia local**, no con llamadas nuevas a SALUTEM. No se
agregan métodos al cliente (D12 intacta; `ClientePersonasPermitidas` no cambia).

## Decisiones (mías, Darío no las revisó todavía)

1. Identidad: `profesional.salutem_profesional_id` (único, nullable). Los profesionales cargados
   a mano en SIGE no lo tienen.
2. Un profesional ya existente sin `salutem_profesional_id` se **adopta** si su nombre coincide
   (comparación sin tildes, sin mayúsculas, espacios colapsados) con el de SALUTEM. Así los que
   sembró la migración 1340 no se duplican.
3. Si SALUTEM cambia el nombre, se actualiza el `nombre` del profesional con origen SALUTEM
   (si choca con otro nombre del catálogo, se deja como está y se registra el error en el ciclo).
4. `activo` no lo toca el sync: una baja manual se respeta. Un profesional nuevo entra activo.
5. El sync agrega `especialidades` (lista de nombres, unión), `sucursales` (lista de nombres),
   `primera_atencion` / `ultima_atencion` (fecha de la primera/última cita en estado Atendido) y
   `sincronizado_en`. `especialidad` (texto libre ya existente) se mantiene editable a mano y,
   si está vacía, el sync la llena con la especialidad más frecuente.
6. Vínculo con el flujo: nueva columna `profesional_id` (FK nullable a `profesional`) en
   `control_medico` y en `ficha_clinica`. El sync de controles y la vinculación de fichas la
   llenan desde `profesionalId`. Los controles manuales (origen CEPA) la toman del selector.
7. Corre en **cada ciclo** del sync (caliente/tibia/fría), después de la vinculación, en modo
   incremental (filas de la copia con `cambiado_en` ≥ inicio de la última ejecución exitosa);
   en `backfill` y `vincular --todo` recorre toda la copia. Un fallo del paso no corta el ciclo
   (mismo patrón que borradores).
8. El botón "Importar desde SALUTEM" sigue existiendo y ahora ejecuta este mismo paso completo.
9. `Ingreso.profesional_id` y la agenda (`disponibilidad_prof`, `propuesta_agenda`) ya apuntan al
   `id` del catálogo; no cambian. Se suma FK solo donde la columna es nueva.

## Backend

- Migración `1350_profesional_salutem`: columnas nuevas en `profesional`
  (`salutem_profesional_id` BigInteger unique nullable, `especialidades` PortableJSON nullable,
  `sucursales` PortableJSON nullable, `primera_atencion` Date, `ultima_atencion` Date,
  `sincronizado_en` DateTime tz), `profesional_id` BigInteger FK nullable + índice en
  `control_medico` y `ficha_clinica`. Nombres de índices/constraints ≤ 30 caracteres (Oracle).
  Compatible Postgres y Oracle 19c (ver migraciones previas).
- `app/services/salutem_sync/profesionales.py`: `sincronizar_profesionales(db, ahora, desde)`
  → resultado con `creados`, `actualizados`, `vinculados`, `errores`. Además re-vincula
  `control_medico` / `ficha_clinica` con `salutem_cita_id` y `profesional_id IS NULL`.
- Orquestador: llamar al paso tras la vinculación, con try/except como borradores.
- `controles.py` y la vinculación de fichas: setear `profesional_id` al crear/actualizar.
- `services/profesionales.py`: `importar_desde_salutem` delega en el paso nuevo (modo completo).
- API: `ProfesionalRead` suma los campos nuevos; `GET /profesionales/{id}/actividad` devuelve
  totales (atenciones por especialidad, controles, pacientes distintos, primera/última atención)
  y las últimas 20 atenciones vinculadas (fecha, especialidad, folio, paciente) — solo lectura,
  mismo RBAC que el listado. `ControlMedicoCreate`/`Read` suman `profesional_id` opcional; si
  viene, el backend valida que exista y usa su nombre como `medico_tratante` cuando éste falte.
- Tests (pytest, BD propia: `TEST_DATABASE_URL=...cepa_test_profesionales`): adopción por
  nombre, alta por id, cambio de nombre, baja manual respetada, incremental vs completo,
  re-vinculación de controles/fichas, orquestador no se corta si el paso falla, endpoint de
  actividad, control manual con `profesional_id`.

## Frontend

- Regenerar `src/types/api.ts` desde el OpenAPI del backend.
- `ProfesionalesPage`: columnas origen (SALUTEM / SIGE), especialidades, última atención y
  "sincronizado hace…"; panel de detalle con la actividad del profesional.
- `NuevoControlDialog`: selector del catálogo (activos) para el médico tratante; envía
  `profesional_id` y el nombre.
- Tests vitest + MSW con las convenciones del repo.

## Fuera de alcance

- Escribir en SALUTEM (D12).
- Datos administrativos que SALUTEM no entrega (RUT del profesional, registro SIS, contrato).
- Reportes por profesional nuevos (el endpoint de actividad es la base para hacerlos después).
