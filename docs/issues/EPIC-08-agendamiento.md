# EPIC-08 — Agendamiento Inteligente

**Módulo PRD:** §7.8 — Agendamiento Inteligente
**Prioridad (MoSCoW):** P1 Should
**Perfiles operativos:** Coordinación · Administrativo · Auditor (NO Clínico — ver Decisiones v4 D1)
**Sprint sugerido:** Sprint 1-2 (Módulo de Agendamiento) — PRD §11.2

> Programación automática de propuestas de agenda diaria, semanal y mensual según la
> disponibilidad de cada profesional. El sistema considera automáticamente: días de reposo
> vigentes en licencias médicas, fechas de próximo control programado y emisión reciente de
> recetas que requieran seguimiento. El agendamiento alimenta los datos de % de adherencia
> (citas realizadas / citas agendadas) que se visualizan en el dashboard (Decisiones v4 D5).

---

## [CEPA-080] Propuesta automática de agenda según disponibilidad

**Épica:** EPIC-08 — Agendamiento Inteligente
**Perfil:** Administrativo | Coordinación (genera/edita) · Auditor (solo lectura)
**Prioridad (MoSCoW):** P1 Should
**Módulo PRD:** 7.8
**Trazabilidad:** PRD §7.8 · §7.6.2 (próximo control) · §7.7 (reposo en licencias) · §7.2.3 (recetas) · §11.2 (Sprint 1-2) · Decisiones v4: D1, D5

### Historia
Como **Administrativo / Coordinación del CEPA**, quiero que el sistema **proponga automáticamente la agenda diaria, semanal y mensual de cada profesional según su disponibilidad, excluyendo los días de reposo vigente y priorizando los controles vencidos o próximos y las recetas recientes que requieren seguimiento** para **organizar la carga de citas sin revisar manualmente licencias, controles y recetas en planillas separadas, y alimentar los indicadores de adherencia del dashboard**.

### Criterios de Aceptación (Gherkin)

- **CA-1 — Propuesta diaria**
  - **Dado** que un Administrativo selecciona un profesional y un día hábil objetivo
  - **Cuando** solicita la propuesta de agenda diaria
  - **Entonces** el sistema genera una lista ordenada de pacientes candidatos a citar ese día, dentro de los bloques de disponibilidad del profesional, sin exceder su cupo diario, excluyendo pacientes con reposo vigente y priorizando controles vencidos/próximos y recetas con seguimiento pendiente.

- **CA-2 — Propuesta semanal**
  - **Dado** que un Administrativo o Coordinación selecciona un profesional y una semana objetivo (lun–vie)
  - **Cuando** solicita la propuesta de agenda semanal
  - **Entonces** el sistema distribuye los pacientes candidatos a lo largo de los días hábiles de la semana respetando la disponibilidad diaria y el cupo por día, sin proponer citas en días de reposo vigente del paciente y balanceando la carga entre los días.

- **CA-3 — Propuesta mensual**
  - **Dado** que un usuario con permiso de generación selecciona un profesional y un mes objetivo
  - **Cuando** solicita la propuesta de agenda mensual
  - **Entonces** el sistema entrega una propuesta consolidada por semanas del mes, respetando la disponibilidad del profesional y la periodicidad de control de cada paciente, marcando los controles vencidos como prioridad alta.

- **CA-4 — Exclusión por reposo vigente**
  - **Dado** un paciente con una licencia médica cuyo período de reposo (inicio–fin) incluye la fecha candidata
  - **Cuando** el sistema arma cualquier propuesta (diaria/semanal/mensual) para esa fecha
  - **Entonces** ese paciente NO es propuesto en los días de reposo vigente, y la propuesta indica el motivo de exclusión ("reposo vigente hasta dd/mm/aaaa").

- **CA-5 — Inclusión y priorización por control próximo/vencido**
  - **Dado** un paciente con un próximo control médico programado (PRD §7.6.2) cuya fecha cae en la ventana de la propuesta
  - **Cuando** el sistema genera la propuesta
  - **Entonces** el paciente se incluye y se prioriza; si el control ya está **vencido** se ubica por sobre los controles solo próximos, y la propuesta muestra la fecha de control y el estado (vencido/próximo).

- **CA-6 — Inclusión por receta reciente con seguimiento**
  - **Dado** un paciente con una receta emitida recientemente (dentro de la ventana de seguimiento, p. ej. fecha de revisión próxima — PRD §7.2.3) que requiere seguimiento
  - **Cuando** el sistema genera la propuesta
  - **Entonces** el paciente se incluye como candidato con la etiqueta "seguimiento de receta", salvo que tenga reposo vigente en la fecha candidata (en cuyo caso la exclusión por reposo prevalece — ver RN-1).

- **CA-7 — Confirmación / descarte y alimentación de adherencia**
  - **Dado** una propuesta de agenda generada
  - **Cuando** el usuario confirma una o más citas propuestas
  - **Entonces** dichas citas quedan **agendadas** y cuentan como "citas agendadas" para el cálculo de % de adherencia del dashboard (Decisiones v4 D5); las propuestas descartadas no generan cita.

- **CA-8 — Permisos por rol**
  - **Dado** un usuario autenticado
  - **Cuando** intenta generar o confirmar una propuesta de agenda
  - **Entonces** solo los perfiles **Administrativo** y **Coordinación** pueden generar/confirmar; el perfil **Auditor** solo puede visualizar las propuestas/agenda (sin editar); cualquier otro acceso es denegado.

### Reglas de Negocio

- **RN-1:** Nunca se propone una cita a un paciente en un día con **reposo vigente** (la fecha candidata está dentro del rango inicio–fin de una licencia médica activa). La exclusión por reposo **prevalece** sobre cualquier criterio de inclusión (control próximo o receta reciente).
- **RN-2:** Prioridad de candidatos en la propuesta, de mayor a menor: (1) control **vencido**, (2) control **próximo** dentro de la ventana, (3) receta reciente con seguimiento pendiente. A igual prioridad, ordenar por antigüedad de la fecha objetivo (más vencido/antiguo primero).
- **RN-3:** Una propuesta nunca excede el **cupo de disponibilidad** del profesional para el día (bloques horarios / cupo máximo diario configurado). El exceso de candidatos se difiere al siguiente día/semana hábil disponible.
- **RN-4:** Solo se consideran **días hábiles** (lun–vie) y los **bloques de disponibilidad** definidos para el profesional. No se proponen citas en fines de semana ni fuera de disponibilidad.
- **RN-5:** "Reposo vigente" se evalúa contra la fecha candidata, no contra la fecha de generación de la propuesta (una propuesta mensual debe excluir reposo día a día).
- **RN-6:** "Receta reciente que requiere seguimiento" se determina por la fecha de emisión/revisión de receta dentro de la ventana de seguimiento parametrizable (PRD §7.2.3); recetas ya gestionadas/cerradas no generan candidatura.
- **RN-7:** Generar y confirmar propuestas está permitido solo a **Administrativo** y **Coordinación**. **Auditor** tiene acceso de solo lectura. El perfil **Clínico** no existe en el sistema (Decisiones v4 D1).
- **RN-8:** Cada cita **agendada** desde una propuesta confirmada incrementa el denominador "citas agendadas" del % de adherencia (Decisiones v4 D5). La realización efectiva de la cita alimenta el numerador "citas realizadas".
- **RN-9:** Toda generación y confirmación de propuesta queda registrada en el **log de auditoría** (quién, qué profesional/paciente, cuándo) — PRD §7.13.

### Test Cases

| ID | Tipo | Precondición | Pasos | Datos | Resultado esperado | Prioridad |
|----|------|--------------|-------|-------|--------------------|-----------|
| TC-080-01 | Positivo | Profesional con disponibilidad lun–vie, cupo 8/día; 5 pacientes con control próximo | Generar propuesta **diaria** para un día hábil | Día objetivo: mar; 5 candidatos sin reposo | Se proponen los 5 pacientes dentro del cupo, ordenados por prioridad, ninguno en reposo | Alta |
| TC-080-02 | Positivo | Profesional disponible toda la semana; 12 candidatos | Generar propuesta **semanal** | Semana lun–vie, cupo 8/día | Los 12 candidatos se distribuyen entre días hábiles sin exceder 8/día ni proponer en sáb/dom | Alta |
| TC-080-03 | Positivo | Profesional disponible el mes; pacientes con periodicidad de control mensual | Generar propuesta **mensual** | Mes objetivo completo | Propuesta consolidada por semanas, respeta disponibilidad; controles vencidos marcados prioridad alta | Alta |
| TC-080-04 | Negativo | Paciente con licencia de reposo total vigente que cubre la fecha candidata | Generar propuesta diaria que incluiría a ese paciente | Reposo 01–10/mm; fecha candidata 05/mm | El paciente **no** aparece en la propuesta; se indica "reposo vigente hasta 10/mm" | Alta |
| TC-080-05 | Positivo | Paciente con control **vencido** y otro con control solo **próximo** | Generar propuesta diaria | Ctrl vencido hace 3 días vs ctrl próximo en 2 días | El control vencido se ordena por sobre el próximo (RN-2) | Alta |
| TC-080-06 | Positivo | Paciente con receta emitida hace 2 días dentro de ventana de seguimiento, sin reposo | Generar propuesta diaria | Receta con revisión próxima | Paciente incluido con etiqueta "seguimiento de receta" | Media |
| TC-080-07 | Borde | Paciente con receta reciente con seguimiento **y** reposo vigente en la misma fecha | Generar propuesta para esa fecha | Receta hace 1 día + reposo 01–10/mm cubre fecha | La exclusión por reposo prevalece (RN-1): paciente **no** propuesto pese a la receta | Alta |
| TC-080-08 | Borde | Profesional con cupo 8/día y 14 candidatos prioritarios para un mismo día | Generar propuesta semanal | 14 candidatos, cupo 8/día | 8 se proponen el día objetivo; los 6 restantes se difieren al siguiente día hábil disponible (RN-3) | Media |
| TC-080-09 | Permisos | Usuario con perfil **Auditor** | Intentar generar/confirmar una propuesta | Sesión Auditor | Acción de generación/confirmación denegada; solo lectura de la propuesta/agenda (RN-7) | Alta |
| TC-080-10 | No funcional (rendimiento) | Base con volúmenes objetivo (1.500+ licencias, 800+ ingresos, 500+ recetas/año) y ~25 profesionales | Generar propuesta **mensual** para un profesional con dataset completo | Mes completo, dataset realista | La propuesta se genera con tiempo de respuesta **< 2 s** (PRD §9 Rendimiento), excluyendo reposo día a día correctamente | Media |

### Definición de Hecho (DoD)
- [ ] Flujo de propuesta diaria/semanal/mensual implementado y desplegado en QA
- [ ] Todos los CA (CA-1 a CA-8) verificados
- [ ] Reglas de exclusión por reposo y priorización (RN-1, RN-2, RN-5) cubiertas por tests
- [ ] Tests unitarios + integración en verde (incl. TC de borde y permisos)
- [ ] Endpoint(s) de generación/confirmación documentados en OpenAPI/Swagger
- [ ] Generación/confirmación registradas en log de auditoría (RN-9)
- [ ] Citas confirmadas alimentan correctamente el denominador de % de adherencia del dashboard (RN-8)
- [ ] Prueba de rendimiento con volúmenes objetivo (< 2 s) ejecutada
- [ ] Demo validada con equipo gestor CEPA

### Notas / Preguntas abiertas
- **Disponibilidad del profesional:** definir fuente y parametrización de los bloques de disponibilidad y cupo diario (¿configurable por Coordinación vía formularios dinámicos PRD §7.13?).
- **Ventana de "receta reciente":** confirmar el umbral de días de la ventana de seguimiento (parametrizable, ligado a fecha de revisión PRD §7.2.3 / D7).
- **Ventana de "control próximo":** confirmar horizonte (p. ej. próximos N días) y tratamiento de controles vencidos.
- **Integración con ficha clínica (SALUTEM/SAM):** el agendamiento real puede vivir en el sistema de fichas; verificar bidireccionalidad y que el aplicativo **no escribe sobre SALUTEM** (Decisiones v4 D12). Definir si CEPA confirma localmente o referencia el agendado externo (PRD §7.6.2 "agendado sí/no").
- **Reposo parcial:** confirmar si el reposo **parcial** (PRD §7.7.1) excluye totalmente o solo en ciertos bloques horarios.
