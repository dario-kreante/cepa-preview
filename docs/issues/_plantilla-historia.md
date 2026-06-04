# Plantilla de Historia de Usuario (issue)

> Estándar para cada historia. Se replica en Markdown (este repo) y en Linear.

## [CEPA-XX] Título de la historia

**Épica:** EPIC-NN — Nombre del módulo
**Perfil:** Administrativo | Coordinación | Auditor
**Prioridad (MoSCoW):** P0 Must | P1 Should | P2 Could
**Módulo PRD:** 7.x
**Trazabilidad:** PRD §7.x.y · Decisiones v4: Dn

### Historia
Como **[perfil]**, quiero **[capacidad]** para **[beneficio]**.

### Criterios de Aceptación (Gherkin)
- **CA-1**
  - **Dado** [contexto]
  - **Cuando** [acción]
  - **Entonces** [resultado esperado]
- **CA-2** …

### Reglas de Negocio
- **RN-1:** [regla invariante / validación / cálculo]
- **RN-2:** …

### Test Cases
| ID | Tipo | Precondición | Pasos | Datos | Resultado esperado | Prioridad |
|----|------|--------------|-------|-------|--------------------|-----------|
| TC-XX-01 | Positivo | … | … | … | … | Alta |
| TC-XX-02 | Negativo | … | … | … | … | Alta |
| TC-XX-03 | Borde | … | … | … | … | Media |

### Definición de Hecho (DoD)
- [ ] CRUD/flujo implementado y desplegado en QA
- [ ] Todos los CA verificados
- [ ] Tests unitarios + integración en verde
- [ ] Endpoint(s) documentados en OpenAPI/Swagger (si aplica)
- [ ] Operaciones registradas en log de auditoría (si aplica)
- [ ] Demo validada con equipo gestor CEPA

### Notas / Preguntas abiertas
- …

---

## Convenciones de Test Cases
- **Tipo:** Positivo (happy path), Negativo (validación/error), Borde (límites/concurrencia), Permisos (RBAC), No funcional (rendimiento/seguridad).
- **ID:** `TC-<nºhistoria>-<correlativo>`.
- Todo cálculo automático (días acumulados, semana de control, % adherencia) lleva al menos 1 TC positivo y 1 de borde.
- Toda historia con RBAC lleva al menos 1 TC de permisos (acceso denegado a perfil sin permiso).
