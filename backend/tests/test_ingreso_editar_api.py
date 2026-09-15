"""BUG-2608-01 — editar la ficha de ingreso después de crearla (CEPA-010).

Se editan los datos del paciente y del ingreso, salvo RUT y folio: el RUT ancla
la integración con SALUTEM y el folio tiene reglas propias (PA-v5-01).
"""

from sqlalchemy import select

from app.models.audit_log import AuditLog


def _crear_ingreso(cliente) -> dict:
    r = cliente.post(
        "/api/v1/ingresos",
        json={
            "rut": "12.345.678-5",
            "nombre": "Juan Pérez",
            "sexo": "M",
            "edad": 40,
            "region": "Maule",
            "diagnostico": "Trastorno adaptativo",
            "tipo_derivacion": "DIAT",
            "tipo_ingreso": "convenio",
            "modelo_tratamiento": "ambulatorio",
            "fecha_ingreso": "2026-06-10",
        },
    )
    assert r.status_code == 201, r.text
    return r.json()


def test_editar_ingreso_persiste_datos_del_paciente_y_del_ingreso(as_admin):
    ingreso = _crear_ingreso(as_admin)

    r = as_admin.put(
        f"/api/v1/ingresos/{ingreso['id']}",
        json={
            "nombre": "Juan Pérez Rojas",
            "telefono": "+56911112222",
            "comuna": "Talca",
            "diagnostico": "Trastorno de ansiedad",
            "tipo_derivacion": "DIEP",
            "fecha_ingreso": "2026-06-12",
        },
    )
    assert r.status_code == 200, r.text
    assert r.json()["diagnostico"] == "Trastorno de ansiedad"
    assert r.json()["folio"] == ingreso["folio"]

    vista = as_admin.get(f"/api/v1/pacientes/{ingreso['paciente_id']}/vista-360").json()
    assert vista["paciente"]["nombre"] == "Juan Pérez Rojas"
    assert vista["paciente"]["telefono"] == "+56911112222"
    assert vista["paciente"]["comuna"] == "Talca"
    assert vista["paciente"]["rut"] == "123456785"
    releido = next(i for i in vista["ingresos"] if i["id"] == ingreso["id"])
    assert releido["tipo_derivacion"] == "DIEP"
    assert releido["fecha_ingreso"] == "2026-06-12"
    # lo no enviado no se toca
    assert releido["modelo_tratamiento"] == "ambulatorio"


def test_editar_ingreso_no_permite_cambiar_rut(as_admin):
    ingreso = _crear_ingreso(as_admin)
    r = as_admin.put(f"/api/v1/ingresos/{ingreso['id']}", json={"rut": "9.876.543-3"})
    assert r.status_code == 422


def test_editar_ingreso_no_permite_cambiar_folio(as_admin):
    ingreso = _crear_ingreso(as_admin)
    r = as_admin.put(f"/api/v1/ingresos/{ingreso['id']}", json={"folio": "F-OTRO"})
    assert r.status_code == 422


def test_editar_ingreso_valida_listas_cerradas(as_admin):
    ingreso = _crear_ingreso(as_admin)
    r = as_admin.put(
        f"/api/v1/ingresos/{ingreso['id']}", json={"tipo_derivacion": "Inventado"}
    )
    assert r.status_code == 422


def test_editar_ingreso_no_acepta_vaciar_obligatorios(as_admin):
    ingreso = _crear_ingreso(as_admin)
    r = as_admin.put(f"/api/v1/ingresos/{ingreso['id']}", json={"diagnostico": None})
    assert r.status_code == 422


def test_editar_ingreso_inexistente_da_404(as_admin):
    r = as_admin.put("/api/v1/ingresos/999999", json={"diagnostico": "X"})
    assert r.status_code == 404


def test_auditor_no_edita_ingreso(as_admin, as_auditor):
    ingreso = _crear_ingreso(as_admin)
    r = as_auditor.put(f"/api/v1/ingresos/{ingreso['id']}", json={"diagnostico": "X"})
    assert r.status_code == 403


def test_editar_ingreso_queda_en_auditoria(as_coordinacion, db_session):
    ingreso = _crear_ingreso(as_coordinacion)
    r = as_coordinacion.put(
        f"/api/v1/ingresos/{ingreso['id']}", json={"diagnostico": "Trastorno de ansiedad"}
    )
    assert r.status_code == 200, r.text

    trazas = db_session.scalars(
        select(AuditLog)
        .where(AuditLog.entity == "ingreso")
        .where(AuditLog.entity_id == str(ingreso["id"]))
        .where(AuditLog.action == "UPDATE")
    ).all()
    assert len(trazas) == 1
    assert trazas[0].actor
