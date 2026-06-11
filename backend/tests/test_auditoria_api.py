"""Tests de integración end-to-end de la API de auditoría.

Cubre CA y TC del spec CEPA-050 y CEPA-051. Los datos se crean vía la sesión
de test (db_session) directamente en los modelos de dominio.

ADAPTACIONES respecto al plan original (declaradas):
- Ingreso: usa fecha_ingreso, tipo_derivacion, estado, diagnostico, modelo_tratamiento.
  No existen fecha_denuncia, tipo_denuncia, estado_caso, programa en Ingreso.
- Seguimiento: campos eval_medica_fecha, eval_psico_fecha, reca_ep_ec, programa.
- Reintegro: modelo CasoReintegro con rut, nombre, tipo_derivacion, fecha_caso, sexo, edad, region.
  alta_psicologica usa fecha_alta_psico (no fecha_alta_psicologica).
"""
from __future__ import annotations

import datetime

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.ingreso import Ingreso
from app.models.paciente import Paciente
from app.models.reintegro import CasoReintegro
from app.models.seguimiento import Seguimiento


# ── Fixture de datos compartida ────────────────────────────────────────────

@pytest.fixture
def caso_completo(db_session: Session) -> dict:
    """Crea un paciente + ingreso + seguimiento en la BD de tests."""
    p = Paciente(
        rut="123456785",
        nombre="Ana González",
        sexo="F",
        edad=35,
        region="Maule",
    )
    db_session.add(p)
    db_session.flush()

    ing = Ingreso(
        paciente_id=p.id,
        folio="2026-0123",
        folio_manual=True,
        numero_siniestro="SIN-2026-001",
        fecha_ingreso=datetime.date(2026, 1, 15),
        tipo_derivacion="DIAT",
        tipo_ingreso="convenio",
        modelo_tratamiento="ambulatorio",
        diagnostico="F32.0 Episodio depresivo leve",
        estado="activo",
    )
    db_session.add(ing)
    db_session.flush()

    seg = Seguimiento(
        ingreso_id=ing.id,
        eval_medica_fecha=datetime.date(2026, 2, 1),
        eval_medica_medico="Dr. Juan Pérez",
        eval_psico_fecha=datetime.date(2026, 2, 5),
        eval_psico_psicologo="Ps. María López",
        reca_ep_ec="F33.1 Trastorno depresivo recurrente",
        programa="Programa ISL",
    )
    db_session.add(seg)
    db_session.flush()

    return {"ingreso_id": ing.id, "folio": ing.folio}


# ── CEPA-050: Vista consolidada del caso ──────────────────────────────────

class TestVistaCasoConsolidado:

    def test_auditor_puede_ver_caso_consolidado_por_ingreso_id(
        self, as_auditor: TestClient, caso_completo: dict
    ):
        """CA-1 / TC-050-01: Auditor abre vista consolidada con §7.5.1–§7.5.4."""
        r = as_auditor.get(f"/api/v1/auditoria/casos/{caso_completo['ingreso_id']}")
        assert r.status_code == 200

        body = r.json()
        assert body["ingreso_id"] == caso_completo["ingreso_id"]

        # §7.5.1
        dc = body["datos_caso"]
        assert dc["folio"] == "2026-0123"
        assert dc["numero_siniestro"] == "SIN-2026-001"
        assert dc["rut"] == "123456785"

        # §7.5.2 — fecha_ingreso → fecha_denuncia, tipo_derivacion → tipo_denuncia
        ev = body["evaluaciones"]
        assert ev["diagnostico_inicial"] == "F32.0 Episodio depresivo leve"
        assert ev["diagnostico_post_reca"] == "F33.1 Trastorno depresivo recurrente"
        assert ev["fecha_eval_medica"] == "2026-02-01"

        # §7.5.3
        ctrl = body["controles"]
        assert ctrl["n_sesiones_medicas"] == 0  # no existe en el modelo real

        # §7.5.4
        cierre = body["cierre"]
        assert cierre["alta_medica"] is False

    def test_coordinacion_puede_ver_caso_consolidado(
        self, as_coordinacion: TestClient, caso_completo: dict
    ):
        """CA-1: Coordinacion también tiene acceso de lectura."""
        r = as_coordinacion.get(f"/api/v1/auditoria/casos/{caso_completo['ingreso_id']}")
        assert r.status_code == 200

    def test_admin_no_puede_ver_caso_consolidado(
        self, as_admin: TestClient, caso_completo: dict
    ):
        """CA-4 / TC-050-06: Administrativo no accede al módulo de auditoría (RBAC)."""
        r = as_admin.get(f"/api/v1/auditoria/casos/{caso_completo['ingreso_id']}")
        assert r.status_code == 403

    def test_sin_token_devuelve_401(self, client: TestClient, caso_completo: dict):
        """TC-050-06: sin sesión activa → 401."""
        r = client.get(f"/api/v1/auditoria/casos/{caso_completo['ingreso_id']}")
        assert r.status_code == 401

    def test_ingreso_inexistente_devuelve_404(self, as_auditor: TestClient):
        """TC-050-06 (variante): ingreso que no existe → 404."""
        r = as_auditor.get("/api/v1/auditoria/casos/999999")
        assert r.status_code == 404

    def test_no_ofrece_endpoint_de_edicion(self, as_auditor: TestClient, caso_completo: dict):
        """CA-4 / TC-050-05: el router no expone métodos de escritura (PUT/PATCH/DELETE)."""
        r_put = as_auditor.put(
            f"/api/v1/auditoria/casos/{caso_completo['ingreso_id']}",
            json={"diagnostico_inicial": "hack"},
        )
        r_patch = as_auditor.patch(
            f"/api/v1/auditoria/casos/{caso_completo['ingreso_id']}",
            json={},
        )
        r_delete = as_auditor.delete(
            f"/api/v1/auditoria/casos/{caso_completo['ingreso_id']}"
        )
        assert r_put.status_code in (404, 405)
        assert r_patch.status_code in (404, 405)
        assert r_delete.status_code in (404, 405)

    def test_caso_sin_altas_cierre_mostrado_como_pendiente(
        self, as_auditor: TestClient, db_session: Session
    ):
        """CA-5 / TC-050-04: cierre vacío no bloquea visualización del resto."""
        p = Paciente(
            rut="987654325",
            nombre="Luis Pérez",
            sexo="M",
            edad=42,
            region="Metropolitana",
        )
        db_session.add(p)
        db_session.flush()

        ing = Ingreso(
            paciente_id=p.id,
            folio="2026-0200",
            folio_manual=True,
            numero_siniestro=None,
            fecha_ingreso=datetime.date(2026, 4, 1),
            tipo_derivacion="DIEP",
            tipo_ingreso="convenio",
            modelo_tratamiento="ambulatorio",
            diagnostico="F41.1",
            estado="activo",
        )
        db_session.add(ing)
        db_session.flush()

        seg = Seguimiento(
            ingreso_id=ing.id,
            eval_medica_fecha=None,
            eval_psico_fecha=None,
            reca_ep_ec=None,
        )
        db_session.add(seg)
        db_session.flush()

        r = as_auditor.get(f"/api/v1/auditoria/casos/{ing.id}")
        assert r.status_code == 200
        body = r.json()
        cierre = body["cierre"]
        assert cierre["alta_medica"] is False
        assert cierre["estado_general"] is None
        # resto de hitos accesible
        assert body["datos_caso"]["folio"] == "2026-0200"


# ── CEPA-050: Búsqueda de casos (listado) ─────────────────────────────────

class TestListadoCasos:

    def test_auditor_puede_listar_casos_con_filtro_rut(
        self, as_auditor: TestClient, caso_completo: dict
    ):
        """CA-1: búsqueda por RUT devuelve los ingresos del paciente."""
        r = as_auditor.get("/api/v1/auditoria/casos", params={"rut": "123456785"})
        assert r.status_code == 200
        body = r.json()
        folios = [c["datos_caso"]["folio"] for c in body]
        assert "2026-0123" in folios

    def test_auditor_puede_listar_casos_con_filtro_folio(
        self, as_auditor: TestClient, caso_completo: dict
    ):
        """CA-1: búsqueda por folio devuelve exactamente ese caso."""
        r = as_auditor.get("/api/v1/auditoria/casos", params={"folio": "2026-0123"})
        assert r.status_code == 200
        body = r.json()
        assert len(body) == 1
        assert body[0]["datos_caso"]["folio"] == "2026-0123"

    def test_siniestros_distintos_aparecen_como_casos_diferenciados(
        self, as_auditor: TestClient, db_session: Session
    ):
        """CA-2 / TC-050-02: dos denuncias bajo el mismo RUT → dos casos diferenciados."""
        p = Paciente(
            rut="112233449",
            nombre="Carlos Rojas",
            sexo="M",
            edad=50,
            region="Biobío",
        )
        db_session.add(p)
        db_session.flush()

        for folio, siniestro, tipo in [
            ("2020-0001", "SIN-2020-DIAT", "DIAT"),
            ("2026-0300", "SIN-2026-DIEP", "DIEP"),
        ]:
            ing = Ingreso(
                paciente_id=p.id,
                folio=folio,
                folio_manual=True,
                numero_siniestro=siniestro,
                fecha_ingreso=datetime.date(2026, 1, 1),
                tipo_derivacion=tipo,
                tipo_ingreso="convenio",
                modelo_tratamiento="ambulatorio",
                diagnostico="F32.0",
                estado="activo",
            )
            db_session.add(ing)
            db_session.flush()
            seg = Seguimiento(
                ingreso_id=ing.id,
                eval_medica_fecha=None,
                eval_psico_fecha=None,
            )
            db_session.add(seg)
        db_session.flush()

        r = as_auditor.get("/api/v1/auditoria/casos", params={"rut": "112233449"})
        assert r.status_code == 200
        body = r.json()
        siniestros = [c["datos_caso"]["numero_siniestro"] for c in body]
        assert "SIN-2020-DIAT" in siniestros
        assert "SIN-2026-DIEP" in siniestros
        # Hitos no mezclados: cada caso tiene su folio correcto
        folios_por_siniestro = {
            c["datos_caso"]["numero_siniestro"]: c["datos_caso"]["folio"] for c in body
        }
        assert folios_por_siniestro["SIN-2020-DIAT"] == "2020-0001"
        assert folios_por_siniestro["SIN-2026-DIEP"] == "2026-0300"


# ── CEPA-051: Reportes de auditoría ───────────────────────────────────────

class TestReportesAuditoria:

    def test_auditor_genera_reporte_con_filtros(
        self, as_auditor: TestClient, caso_completo: dict
    ):
        """CA-1 / TC-051-01: reporte filtrando por período y estado devuelve filas correctas."""
        payload = {
            "fecha_desde": "2026-01-01",
            "fecha_hasta": "2026-12-31",
            "estado_caso": "activo",
        }
        r = as_auditor.post("/api/v1/auditoria/reportes", json=payload)
        assert r.status_code == 200
        body = r.json()
        assert "filas" in body
        assert "total" in body
        assert "filtros_aplicados" in body
        assert body["filtros_aplicados"]["estado_caso"] == "activo"
        folios = [f["folio"] for f in body["filas"]]
        assert "2026-0123" in folios

    def test_admin_no_puede_generar_reporte(self, as_admin: TestClient):
        """TC-051-06: Administrativo no puede generar reportes de auditoría."""
        payload = {"fecha_desde": "2026-01-01", "fecha_hasta": "2026-12-31"}
        r = as_admin.post("/api/v1/auditoria/reportes", json=payload)
        assert r.status_code == 403

    def test_sin_token_reporte_devuelve_401(self, client: TestClient):
        """TC-051-06: sin sesión → 401."""
        payload = {"fecha_desde": "2026-01-01", "fecha_hasta": "2026-12-31"}
        r = client.post("/api/v1/auditoria/reportes", json=payload)
        assert r.status_code == 401

    def test_reporte_vacio_devuelve_200_con_total_cero(self, as_auditor: TestClient):
        """CA-4 / TC-051-04: filtros sin coincidencias → 200 con lista vacía, no error."""
        payload = {"fecha_desde": "2000-01-01", "fecha_hasta": "2000-12-31"}
        r = as_auditor.post("/api/v1/auditoria/reportes", json=payload)
        assert r.status_code == 200
        body = r.json()
        assert body["total"] == 0
        assert body["filas"] == []

    def test_descarga_csv_contiene_filas_trazables(
        self, as_auditor: TestClient, caso_completo: dict
    ):
        """CA-2 / TC-051-02: descarga en CSV conserva filtros como metadatos (encabezado)
        y cada fila es trazable por folio + número de siniestro (CA-3 / TC-051-03).
        """
        payload = {"fecha_desde": "2026-01-01", "fecha_hasta": "2026-12-31"}
        r = as_auditor.post("/api/v1/auditoria/reportes/descargar", json=payload)
        assert r.status_code == 200
        assert "text/csv" in r.headers.get("content-type", "")
        cd = r.headers.get("content-disposition", "")
        assert "attachment" in cd

        contenido = r.text
        # Primera línea: encabezados con folio y numero_siniestro (trazabilidad)
        encabezados = contenido.splitlines()[0].split(",")
        assert "folio" in encabezados
        assert "numero_siniestro" in encabezados
        assert "ingreso_id" in encabezados

        # Al menos una fila de datos
        lineas = contenido.splitlines()
        assert len(lineas) >= 2

    def test_descarga_admin_denegada(self, as_admin: TestClient):
        """TC-051-06: Administrativo no puede descargar reportes de auditoría."""
        payload = {"fecha_desde": "2026-01-01", "fecha_hasta": "2026-12-31"}
        r = as_admin.post("/api/v1/auditoria/reportes/descargar", json=payload)
        assert r.status_code == 403

    def test_reporte_sin_periodo_devuelve_422(self, as_auditor: TestClient):
        """RN-2: el período es obligatorio; sin fecha_desde → 422."""
        r = as_auditor.post("/api/v1/auditoria/reportes", json={"estado_caso": "activo"})
        assert r.status_code == 422

    def test_filas_son_trazables_por_folio_y_siniestro(
        self, as_auditor: TestClient, caso_completo: dict
    ):
        """CA-3 / TC-051-03: cada fila contiene folio + numero_siniestro + ingreso_id."""
        payload = {"fecha_desde": "2026-01-01", "fecha_hasta": "2026-12-31"}
        r = as_auditor.post("/api/v1/auditoria/reportes", json=payload)
        assert r.status_code == 200
        body = r.json()
        for fila in body["filas"]:
            assert "folio" in fila
            assert "ingreso_id" in fila
            # numero_siniestro puede ser None para casos sin siniestro registrado
            assert "numero_siniestro" in fila
