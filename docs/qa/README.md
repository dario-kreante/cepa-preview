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

## Ejecución

Los test cases nacen en estado "Pendiente" (columna Estado en cada tabla / columna Status en el Excel). A medida que se ejecutan, esa columna se actualiza a Pass/Fail/Blocked y el detalle (entorno, evidencia, hallazgos) queda en [`execution-log/`](./execution-log/), un archivo por corrida.

| Corrida | Alcance | Resultado | Detalle |
|---|---|---|---|
| 2026-07-02 | EPIC-00 (24 TCs) — piloto en ambiente local | 22 Pass, 2 Fail | [`execution-log/EPIC-00-run-2026-07-02.md`](./execution-log/EPIC-00-run-2026-07-02.md) |
| 2026-07-04 | EPIC-01 (54 TCs) — piloto en ambiente local | 30 Pass, 24 Fail | [`execution-log/EPIC-01-run-2026-07-04.md`](./execution-log/EPIC-01-run-2026-07-04.md) |
| 2026-07-04 | EPIC-02 (30 TCs) — piloto en ambiente local | 22 Pass, 8 Fail | [`execution-log/EPIC-02-run-2026-07-04.md`](./execution-log/EPIC-02-run-2026-07-04.md) |
| 2026-07-04 | EPIC-03 (26 TCs) — piloto en ambiente local | 17 Pass, 9 Fail | [`execution-log/EPIC-03-run-2026-07-04.md`](./execution-log/EPIC-03-run-2026-07-04.md) |
| 2026-07-04 | EPIC-04 (29 TCs) — piloto en ambiente local | 19 Pass, 10 Fail | [`execution-log/EPIC-04-run-2026-07-04.md`](./execution-log/EPIC-04-run-2026-07-04.md) |
| 2026-07-04 | EPIC-05 (20 TCs) — piloto en ambiente local | 11 Pass, 8 Fail, 1 Bloqueado | [`execution-log/EPIC-05-run-2026-07-04.md`](./execution-log/EPIC-05-run-2026-07-04.md) |
| 2026-07-04 | EPIC-06 (25 TCs) — piloto en ambiente local | 21 Pass, 4 Fail | [`execution-log/EPIC-06-run-2026-07-04.md`](./execution-log/EPIC-06-run-2026-07-04.md) |
| 2026-07-04 | EPIC-07 (40 TCs) — piloto en ambiente local | 31 Pass, 9 Fail | [`execution-log/EPIC-07-run-2026-07-04.md`](./execution-log/EPIC-07-run-2026-07-04.md) |
| 2026-07-04 | EPIC-08 (17 TCs) — piloto en ambiente local | 9 Pass, 7 Fail, 1 Bloqueado | [`execution-log/EPIC-08-run-2026-07-04.md`](./execution-log/EPIC-08-run-2026-07-04.md) |
| 2026-07-04 | EPIC-09 (54 TCs) — piloto en ambiente local | 31 Pass, 21 Fail, 2 Bloqueado | [`execution-log/EPIC-09-run-2026-07-04.md`](./execution-log/EPIC-09-run-2026-07-04.md) |
| 2026-07-04 | EPIC-10 (36 TCs) — piloto en ambiente local | 29 Pass, 6 Fail, 1 Bloqueado | [`execution-log/EPIC-10-run-2026-07-04.md`](./execution-log/EPIC-10-run-2026-07-04.md) |
| 2026-07-04 | EPIC-11 (24 TCs) — piloto en ambiente local | 22 Pass, 2 Fail | [`execution-log/EPIC-11-run-2026-07-04.md`](./execution-log/EPIC-11-run-2026-07-04.md) |
| 2026-07-04 | EPIC-12 (23 TCs) — piloto en ambiente local | 13 Pass, 10 Fail | [`execution-log/EPIC-12-run-2026-07-04.md`](./execution-log/EPIC-12-run-2026-07-04.md) |

**Cobertura total: 402/402 TCs ejecutados (EPIC-00 a EPIC-12).** Resultado agregado de las 13 corridas: 277 Pass, 120 Fail, 5 Bloqueado. Ver el detalle de resultados y hallazgos de cada corrida en la tabla anterior y en `execution-log/`.

## Convenciones
- **ID:** `TC-CEPA-XXX-NNN` (historia + correlativo).
- **Comments:** S1 happy path · S2 borde · S3 excepción de negocio/permisos · S4 validación · BR-n regla sin CA · PLANILLA cobertura Anexo 4.
- **Estado de ejecución** se registra en el Excel (columna Status) o en la columna Estado de cada tabla markdown.
