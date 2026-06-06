# Decisiones de la revisión v4 (comentarios de la contraparte CEPA)

> Cambios de alcance y reglas de negocio derivados de los comentarios del documento
> `PRD_Sistema_CEPA_v4_Comentarios.docx` (María del Pilar García Zerene, Carla Mendoza Núñez,
> Adm Cepa, Coordinadora Convenio ISL — abril 2026). **Estos cambios son autoritativos y
> ya están incorporados en las historias de usuario de este backlog.**

## D1. El perfil Clínico NO tendrá acceso al sistema
- Los profesionales clínicos (psicólogos, médicos, psiquiatras) **no usan el Sistema CEPA**:
  revisan y registran información clínica directamente en las fichas clínicas de **SALUTEM/SAM**.
- **Impacto:** las historias de usuario del perfil "Clínico" (sección 6.2 del PRD) se
  **reasignan al perfil Administrativo** o se **eliminan**. El EPT (Estudio de Puesto de Trabajo)
  lo gestiona un **funcionario administrativo**, no un EPTista clínico.
- **RBAC:** se mantienen 3 perfiles operativos: **Coordinación, Administrativo, Auditor**
  (se quita "Clínico"). Aumentar cantidad de Coordinación, Administrativos y Auditores.
  Los números de usuarios por perfil quedan abiertos (alta rotación en CEPA).

## D2. Folios: autogenerados con opción manual
- El folio es secuencial automático, **pero debe existir opción de ingreso manual** para:
  - **Reingresos** (el usuario reingresa tras el alta y **mantiene el folio anterior**).
  - Folios **pre-asignados** que ya existen en las planillas Excel históricas.
  - Ingresos recibidos **después de las 15:00 (lun–jue)** que corresponden cargarse con la
    fecha del día hábil siguiente.
- **Reingresos vs. nuevas denuncias bajo el mismo RUT:** una persona puede tener una DIAT (2020)
  y una DIEP (2026). Se diferencian por **número de siniestro**; se evalúa si generar nuevo folio
  o diferenciar por siniestro.

## D3. ODAS (Órdenes de Primera Atención) — requisito nuevo
- Las **ODAS** son documentos administrativos con **plazo de vigencia/vencimiento**, no están
  en la ficha clínica → se ingresan manualmente.
- Se requiere: **registro de ODA**, **fecha de vencimiento de ODA**, **alerta de ODAS por vencer**
  y **reporte de ODAS vencidas**.

## D4. Tipos de derivación (valores reales)
DIEP · DIAT · PAPT a flujo AT · Reingreso FUMP · Reingreso SUSESO · Convenio U.Clínica ·
Proyecto · Particular · PAPT. (El antiguo "convenio SOCORRO" ya no existe.)

## D5. Métricas y dashboard
- **% de adherencia al tratamiento** = `nº de citas realizadas / nº de citas agendadas`.
- **% de avance del tratamiento:** medir etapa del tratamiento (ej. 10/15/21 sesiones), sesiones
  restantes para posible alta e indicadores en % por plan de tratamiento; incluir **aumentos de
  sesiones entregadas por ISL**.
- Dashboard **multiprograma** (gestión integral del CEPA, no de un solo programa).
- Filtros/dimensiones requeridos: diagnósticos, tipos de alta, tramos etarios, sexo,
  zona geográfica (región, comuna), modelo de tratamiento, tipo de ingreso
  (consulta espontánea, convenio, proyecto), profesional, programa.
- **QA de métricas:** cada métrica requiere validación de resultado y de proceso
  (persona vs. programador). Definir responsable de QA de métricas.

## D6. Campos obligatorios y calidad de datos
- Asegurar campos obligatorios para información **limpia, fidedigna y comparable**:
  sexo, edad, diagnóstico, modelo de tratamiento, tipos de alta, tipo de ingreso, tipo de convenio.
- Al configurar campos (formularios dinámicos) debe garantizarse que el formulario quede
  **bien parametrizado** (validación técnica de la configuración).

## D7. Fármacos
- Registrar **esquema farmacológico** y **estadísticas de fármacos** utilizados por
  tratamiento, programa y profesional.
- Contemplar **fármacos extra-sistema** y **licencias médicas extra-sistema**.

## D8. Licencias médicas (datos adicionales)
- Registrar: cantidad de días de reposo, inicio del reposo, fecha de emisión, fin del reposo,
  tipo de licencia, indicación de reposo, diagnóstico, tipo de reposo (total/parcial).

## D9. Consentimiento informado
- Es **campo obligatorio para iniciar tratamiento** → se requiere **validador de consentimiento
  firmado**. Definir cómo se adjunta / de dónde proviene esa información.

## D10. Validadores de plazos por programa
- La evaluación (psicólogo y médico) debe realizarse en los **plazos establecidos por programa**;
  el sistema debe tener un **validador de estado** que indique cumplimiento de plazos.

## D11. Tipificación de altas
- En evaluación: posiblemente **una sola fecha de alta** (última atención) independiente del tipo,
  para simplificar. Decisión pendiente de confirmar con Coordinación.

## D12. Comunicaciones
- **Correo electrónico solo para alertas.** Lectura de PDF se considera **P1** (no P2).
- Integración con ficha clínica: **no es unidireccional** (revisar bidireccionalidad). El aplicativo
  **no escribe sobre SALUTEM**.

## D13. Gobernanza
- Sumar a **Mario (Director de TI UTalca)** como contraparte técnica; valida y supervisa
  seguridad, cumplimiento e integraciones.
- Posibilidad de **manual de usuario**. Capacitar al **100% de funcionarios activos** con acceso.
