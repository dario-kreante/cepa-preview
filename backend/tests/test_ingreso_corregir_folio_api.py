"""Corrección del folio desde la ficha: solo Administrativo; el cambio arrastra lo que
guarda el folio como texto (reingresos, fichas clínicas, IMED) y queda en la auditoría."""

from datetime import date

from sqlalchemy import select

from app.models.audit_log import AuditLog
from app.models.ficha_clinica import FichaClinica
from app.models.imed_payload import ImedPayload
from app.models.ingreso import Ingreso


def _crear_ingreso(cliente, rut="12.345.678-5", folio=None) -> dict:
    body = {
        "rut": rut,
        "nombre": "Juan Pérez",
        "sexo": "M",
        "edad": 40,
        "region": "Maule",
        "diagnostico": "Trastorno adaptativo",
        "tipo_derivacion": "DIAT",
        "tipo_ingreso": "convenio",
        "modelo_tratamiento": "ambulatorio",
        "fecha_ingreso": "2026-06-10",
    }
    if folio:
        body["folio"] = folio
    r = cliente.post("/api/v1/ingresos", json=body)
    assert r.status_code == 201, r.text
    return r.json()


def test_administrativo_corrige_el_folio_y_queda_auditado(as_admin, db_session):
    ingreso = _crear_ingreso(as_admin)
    anterior = ingreso["folio"]
    db_session.add(
        FichaClinica(ingreso_id=ingreso["id"], folio=anterior, origen="SALUTEM", contenido={})
    )
    db_session.add(ImedPayload(folio=anterior, tipo="licencia", datos={}))
    db_session.commit()

    r = as_admin.put(f"/api/v1/ingresos/{ingreso['id']}/folio", json={"folio": "  F-2026-0999 "})

    assert r.status_code == 200, r.text
    assert r.json()["folio"] == "F-2026-0999"
    assert r.json()["folio_manual"] is True
    db_session.expire_all()
    assert db_session.scalars(select(FichaClinica.folio)).all() == ["F-2026-0999"]
    assert db_session.scalars(select(ImedPayload.folio)).all() == ["F-2026-0999"]
    # valor_nuevo es CLOB en Oracle: no se compara en el WHERE (ORA-22848).
    trazas = db_session.scalars(
        select(AuditLog).where(
            AuditLog.entity == "ingreso", AuditLog.entity_id == str(ingreso["id"])
        )
    ).all()
    traza = next(t for t in trazas if t.valor_nuevo == "F-2026-0999")
    assert traza.valor_anterior == anterior
    assert traza.actor == "admin_test"


def test_el_folio_de_otro_paciente_se_rechaza(as_admin):
    uno = _crear_ingreso(as_admin)
    otro = _crear_ingreso(as_admin, rut="9.876.543-3")
    r = as_admin.put(f"/api/v1/ingresos/{uno['id']}/folio", json={"folio": otro["folio"]})
    assert r.status_code == 409
    assert "otro paciente" in r.json()["detail"]


def test_los_reingresos_con_el_mismo_folio_cambian_juntos(as_admin, db_session):
    ingreso = _crear_ingreso(as_admin)
    base = db_session.get(Ingreso, ingreso["id"])
    reingreso = Ingreso(
        paciente_id=base.paciente_id,
        folio=base.folio,
        fecha_ingreso=date(2026, 9, 1),
        tipo_derivacion=base.tipo_derivacion,
        tipo_ingreso=base.tipo_ingreso,
        modelo_tratamiento=base.modelo_tratamiento,
        diagnostico=base.diagnostico,
    )
    db_session.add(reingreso)
    db_session.commit()

    r = as_admin.put(f"/api/v1/ingresos/{ingreso['id']}/folio", json={"folio": "F-NUEVO"})
    assert r.status_code == 200, r.text
    db_session.expire_all()
    assert db_session.get(Ingreso, reingreso.id).folio == "F-NUEVO"


def test_folio_vacio_se_rechaza(as_admin):
    ingreso = _crear_ingreso(as_admin)
    r = as_admin.put(f"/api/v1/ingresos/{ingreso['id']}/folio", json={"folio": "   "})
    assert r.status_code == 422


def test_ingreso_inexistente_da_404(as_admin):
    r = as_admin.put("/api/v1/ingresos/999999/folio", json={"folio": "F-X"})
    assert r.status_code == 404


def test_coordinacion_y_auditor_no_pueden_corregir_el_folio(as_admin, as_coordinacion, as_auditor):
    ingreso = _crear_ingreso(as_admin)
    for cliente in (as_coordinacion, as_auditor):
        r = cliente.put(f"/api/v1/ingresos/{ingreso['id']}/folio", json={"folio": "F-X"})
        assert r.status_code == 403
