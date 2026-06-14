"""Tests de integración — CEPA-041: Proceso RECA y medidas correctivas.

DEVIATION-1: RUT plan original '7.876.543-K' tiene DV inválido.
Sustituido por '9.876.543-3' (DV válido verificado con normalizar_rut).
"""


def _crear_caso(as_admin) -> int:
    """Crea ingreso + caso de reintegro y devuelve caso_id."""
    ing = as_admin.post(
        "/api/v1/ingresos",
        json={
            "rut": "9.876.543-3",
            "nombre": "Ana Torres",
            "sexo": "F",
            "edad": 35,
            "region": "Maule",
            "diagnostico": "EP lumbar",
            "tipo_derivacion": "DIEP",
            "tipo_ingreso": "convenio",
            "modelo_tratamiento": "ambulatorio",
            "fecha_ingreso": "2026-03-01",
        },
    )
    assert ing.status_code == 201
    ingreso_id = ing.json()["id"]
    caso = as_admin.post(
        "/api/v1/reintegros",
        json={
            "ingreso_id": ingreso_id,
            "rut": "9.876.543-3",
            "nombre": "Ana Torres",
            "tipo_derivacion": "DIEP",
            "fecha_caso": "2026-03-01",
            "sexo": "F",
            "edad": 35,
            "region": "Maule",
        },
    )
    assert caso.status_code == 201
    return caso.json()["id"]


def _payload_reca(**over):
    base = {
        "fecha_reca": "2026-03-05",
        "tipo_reca": "EP",
        "numero_reca": "2026-0042",
        "razon_social": "Empresa Ltda.",
        "riesgos_calificados": "Carga manual, postura forzada",
        "solicita_medidas": False,
    }
    base.update(over)
    return base


# TC-041-01: crear RECA con datos completos → asociada al caso
def test_crear_reca_exitoso(as_admin):
    caso_id = _crear_caso(as_admin)
    r = as_admin.post(f"/api/v1/reintegros/{caso_id}/reca", json=_payload_reca())
    assert r.status_code == 201, r.text
    cuerpo = r.json()
    assert cuerpo["numero_reca"] == "2026-0042"
    assert cuerpo["caso_reintegro_id"] == caso_id


# TC-041-01 (bis): RECA visible desde GET y en lectura de auditor
def test_reca_visible_y_auditor_puede_leer(as_admin, as_auditor):
    caso_id = _crear_caso(as_admin)
    as_admin.post(f"/api/v1/reintegros/{caso_id}/reca", json=_payload_reca())
    r = as_auditor.get(f"/api/v1/reintegros/{caso_id}/reca")
    assert r.status_code == 200
    assert r.json()["numero_reca"] == "2026-0042"


# TC-041-02: ciclo de medida completo (fecha medida < fecha verificación)
def test_ciclo_medidas_completo(as_admin):
    caso_id = _crear_caso(as_admin)
    r = as_admin.post(
        f"/api/v1/reintegros/{caso_id}/reca",
        json=_payload_reca(
            solicita_medidas=True,
            detalle_medidas="Reducir carga manual",
            fecha_medidas="2026-03-10",
            verifica_medidas=True,
            detalle_verificacion="Medida implementada",
            fecha_verificacion="2026-03-25",
        ),
    )
    assert r.status_code == 201
    cuerpo = r.json()
    assert cuerpo["verifica_medidas"] is True
    assert cuerpo["fecha_verificacion"] == "2026-03-25"


# TC-041-03: solicita_medidas=True sin detalle → 422
def test_medidas_sin_detalle_rechazado(as_admin):
    caso_id = _crear_caso(as_admin)
    r = as_admin.post(
        f"/api/v1/reintegros/{caso_id}/reca",
        json=_payload_reca(
            solicita_medidas=True,
            detalle_medidas=None,
            fecha_medidas="2026-03-10",
        ),
    )
    assert r.status_code == 422


# TC-041-03 (bis): solicita_medidas=True sin fecha_medidas → 422
def test_medidas_sin_fecha_rechazado(as_admin):
    caso_id = _crear_caso(as_admin)
    r = as_admin.post(
        f"/api/v1/reintegros/{caso_id}/reca",
        json=_payload_reca(
            solicita_medidas=True,
            detalle_medidas="Ajuste puesto",
            fecha_medidas=None,
        ),
    )
    assert r.status_code == 422


# TC-041-04: verificación anterior a medida → 422
def test_verificacion_anterior_a_medida_rechazado(as_admin):
    caso_id = _crear_caso(as_admin)
    r = as_admin.post(
        f"/api/v1/reintegros/{caso_id}/reca",
        json=_payload_reca(
            solicita_medidas=True,
            detalle_medidas="Ajuste puesto",
            fecha_medidas="2026-03-10",
            verifica_medidas=True,
            detalle_verificacion="ok",
            fecha_verificacion="2026-03-05",  # anterior a fecha_medidas
        ),
    )
    assert r.status_code == 422


# TC-041-05: número de RECA duplicado → 409
def test_numero_reca_duplicado_rechazado(as_admin):
    caso_id = _crear_caso(as_admin)
    as_admin.post(f"/api/v1/reintegros/{caso_id}/reca", json=_payload_reca())
    r = as_admin.post(f"/api/v1/reintegros/{caso_id}/reca", json=_payload_reca())
    assert r.status_code == 409


# TC-041-06: Auditor no puede editar medidas → 403
def test_auditor_no_puede_crear_reca(as_auditor):
    r = as_auditor.post(
        "/api/v1/reintegros/1/reca",
        json=_payload_reca(),
    )
    assert r.status_code == 403


# Actualizar medidas via PATCH
def test_actualizar_reca_patch(as_admin):
    caso_id = _crear_caso(as_admin)
    as_admin.post(f"/api/v1/reintegros/{caso_id}/reca", json=_payload_reca())
    r = as_admin.patch(
        f"/api/v1/reintegros/{caso_id}/reca",
        json={"riesgos_calificados": "Actualizado"},
    )
    assert r.status_code == 200
    assert r.json()["riesgos_calificados"] == "Actualizado"
