# QA — Test Cases y Trazabilidad · Sistema CEPA

Suite de test cases generada el **2026-07-02** a partir de:
- Épicas e historias del backlog ([`docs/issues/`](../issues/)) — PRD Sistema CEPA v1.0 + decisiones v4.
- **Planilla CEPA sin datos (Anexo 4)**: hojas Ingresos, Gestión de Fármacos, Seguimiento EPT, Seguimiento Reintegro, Auditoría, Controles Médicos, Licencias Médicas (cobertura de campos como TCs de *Data Integrity*).

**Total: 402 test cases · 48 historias cubiertas (100% de las historias del backlog).**

- Excel ejecutable: [`TestCases_RTM_2026-07-02.xlsx`](./TestCases_RTM_2026-07-02.xlsx) (hojas: Test Cases, RTM, Resumen Ejecutivo; columnas Actual Result/Status/Tester/Test Date para ejecución).
- Trazabilidad: [`RTM.md`](./RTM.md).

## Test cases por épica

| Épica | Archivo | Historias | TCs |
|---|---|---|---|
| EPIC-00 — Plataforma base, Autenticación y RBAC | [`test-cases/TC-EPIC-00.md`](./test-cases/TC-EPIC-00.md) | 3 | 24 |
| EPIC-01 — Ingresos y Gestión de Pacientes | [`test-cases/TC-EPIC-01.md`](./test-cases/TC-EPIC-01.md) | 7 | 54 |
| EPIC-02 — Gestión de Fármacos | [`test-cases/TC-EPIC-02.md`](./test-cases/TC-EPIC-02.md) | 4 | 30 |
| EPIC-03 — Seguimiento EPT (Estudio de Puesto de Trabajo) | [`test-cases/TC-EPIC-03.md`](./test-cases/TC-EPIC-03.md) | 3 | 26 |
| EPIC-04 — Seguimiento de Reintegro | [`test-cases/TC-EPIC-04.md`](./test-cases/TC-EPIC-04.md) | 3 | 29 |
| EPIC-05 — Auditoría | [`test-cases/TC-EPIC-05.md`](./test-cases/TC-EPIC-05.md) | 2 | 20 |
| EPIC-06 — Controles Médicos | [`test-cases/TC-EPIC-06.md`](./test-cases/TC-EPIC-06.md) | 3 | 25 |
| EPIC-07 — Licencias Médicas | [`test-cases/TC-EPIC-07.md`](./test-cases/TC-EPIC-07.md) | 4 | 40 |
| EPIC-08 — Agendamiento Inteligente | [`test-cases/TC-EPIC-08.md`](./test-cases/TC-EPIC-08.md) | 1 | 17 |
| EPIC-09 — Reportería y Dashboard | [`test-cases/TC-EPIC-09.md`](./test-cases/TC-EPIC-09.md) | 8 | 54 |
| EPIC-10 — Alertas y Notificaciones | [`test-cases/TC-EPIC-10.md`](./test-cases/TC-EPIC-10.md) | 4 | 36 |
| EPIC-11 — Configurabilidad y Calidad de Datos | [`test-cases/TC-EPIC-11.md`](./test-cases/TC-EPIC-11.md) | 3 | 24 |
| EPIC-12 — API de Integración | [`test-cases/TC-EPIC-12.md`](./test-cases/TC-EPIC-12.md) | 3 | 23 |

## Distribución

| Dimensión | Valores |
|---|---|
| Categoría | Functional: 165 · Business Rules: 124 · Security: 65 · Data Integrity: 29 · Integration: 10 · Performance: 6 · UI/UX: 2 · Regression: 1 |
| Prioridad | P0: 343 · P1: 52 · P2: 7 |
| Severidad | Critical: 154 · Major: 197 · Medium: 50 · Low: 1 |

## Convenciones
- **ID:** `TC-CEPA-XXX-NNN` (historia + correlativo).
- **Comments:** S1 happy path · S2 borde · S3 excepción de negocio/permisos · S4 validación · BR-n regla sin CA · PLANILLA cobertura Anexo 4.
- **Estado de ejecución** se registra en el Excel (columna Status) o en la columna Estado de cada tabla markdown.
