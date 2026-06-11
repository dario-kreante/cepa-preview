"""Tests de CEPA-023: seguimiento de tratamiento (disminución / cambio de esquema).

Nota: los RUTs del plan original tenían DV inválidos; se usan equivalentes
con DV correcto (verificado con app/util/rut.py):
  12.121.212-9, 13.131.313-6, 14.141.414-3, 15.151.515-0,
  16.161.616-8, 17.171.717-5, 18.181.818-2, 19.191.919-K
"""


def _setup_registro(client, rut: str = "12.121.212-9") -> int:
    ingreso_r = client.post(
        "/api/v1/ingresos",
        json={
            "rut": rut,
            "nombre": "Paciente Seguimiento",
            "sexo": "M",
            "edad": 45,
            "region": "Maule",
            "diagnostico": "F33",
            "tipo_derivacion": "DIAT",
            "tipo_ingreso": "convenio",
            "modelo_tratamiento": "ambulatorio",
            "fecha_ingreso": "2026-06-10",
        },
    )
    assert ingreso_r.status_code == 201, ingreso_r.text
    ingreso_id = ingreso_r.json()["id"]
    reg_r = client.post(
        "/api/v1/registro-farmacologico",
        json={
            "ingreso_id": ingreso_id,
            "medico_tratante": "Dr. Ramos",
            "estado_farmacologico": "activo",
        },
    )
    assert reg_r.status_code == 201, reg_r.text
    return ingreso_id


# TC-023-01: CA-3 — disminución=No, cambio=No, solo observaciones → OK
def test_seguimiento_solo_observaciones(as_admin):
    ingreso_id = _setup_registro(as_admin)
    r = as_admin.post(
        f"/api/v1/registro-farmacologico/{ingreso_id}/seguimiento",
        json={
            "disminucion_farmacos": False,
            "cambio_esquema": False,
            "observaciones": "Paciente estable.",
        },
    )
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["disminucion_farmacos"] is False
    assert body["cambio_esquema"] is False
    assert body["observaciones"] == "Paciente estable."
    assert body["plan_disminucion"] is None
    assert body["detalle_cambio"] is None


# TC-023-01: disminución=Sí con plan → OK
def test_seguimiento_disminucion_con_plan(as_admin):
    ingreso_id = _setup_registro(as_admin, rut="13.131.313-6")
    r = as_admin.post(
        f"/api/v1/registro-farmacologico/{ingreso_id}/seguimiento",
        json={
            "disminucion_farmacos": True,
            "plan_disminucion": "Bajar 25 mg/semana hasta suspender.",
            "cambio_esquema": False,
        },
    )
    assert r.status_code == 201, r.text
    assert r.json()["plan_disminucion"] == "Bajar 25 mg/semana hasta suspender."


# TC-023-02: CA-1 — disminución=Sí sin plan → 422
def test_disminucion_sin_plan_rechazada(as_admin):
    ingreso_id = _setup_registro(as_admin, rut="14.141.414-3")
    r = as_admin.post(
        f"/api/v1/registro-farmacologico/{ingreso_id}/seguimiento",
        json={"disminucion_farmacos": True, "cambio_esquema": False},
    )
    assert r.status_code == 422
    assert "plan_disminucion" in r.text


# TC-023-03: CA-2 — cambio de esquema=Sí sin detalle → 422
def test_cambio_esquema_sin_detalle_rechazado(as_admin):
    ingreso_id = _setup_registro(as_admin, rut="15.151.515-0")
    r = as_admin.post(
        f"/api/v1/registro-farmacologico/{ingreso_id}/seguimiento",
        json={"disminucion_farmacos": False, "cambio_esquema": True},
    )
    assert r.status_code == 422
    assert "detalle_cambio" in r.text


# TC-023-01 completo: disminución=Sí + cambio=No + observaciones
def test_seguimiento_completo_disminucion(as_admin):
    ingreso_id = _setup_registro(as_admin, rut="16.161.616-8")
    r = as_admin.post(
        f"/api/v1/registro-farmacologico/{ingreso_id}/seguimiento",
        json={
            "disminucion_farmacos": True,
            "plan_disminucion": "Bajar 25 mg/semana.",
            "cambio_esquema": False,
            "observaciones": "Revisión semanal.",
        },
    )
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["plan_disminucion"] == "Bajar 25 mg/semana."
    assert body["observaciones"] == "Revisión semanal."


# Listar seguimientos del folio
def test_listar_seguimientos(as_admin):
    ingreso_id = _setup_registro(as_admin, rut="17.171.717-5")
    as_admin.post(
        f"/api/v1/registro-farmacologico/{ingreso_id}/seguimiento",
        json={"disminucion_farmacos": False, "cambio_esquema": False},
    )
    r = as_admin.get(f"/api/v1/registro-farmacologico/{ingreso_id}/seguimiento")
    assert r.status_code == 200
    assert len(r.json()) >= 1


# TC-023-05: Auditor no puede crear seguimiento → 403
def test_auditor_no_puede_crear_seguimiento(as_auditor, as_admin):
    ingreso_id = _setup_registro(as_admin, rut="18.181.818-2")
    r = as_auditor.post(
        f"/api/v1/registro-farmacologico/{ingreso_id}/seguimiento",
        json={"disminucion_farmacos": False, "cambio_esquema": False},
    )
    assert r.status_code == 403


# TC-023-05: Auditor puede leer seguimiento → 200
def test_auditor_puede_leer_seguimiento(as_auditor, as_admin):
    ingreso_id = _setup_registro(as_admin, rut="19.191.919-K")
    as_admin.post(
        f"/api/v1/registro-farmacologico/{ingreso_id}/seguimiento",
        json={"disminucion_farmacos": False, "cambio_esquema": False},
    )
    r = as_auditor.get(f"/api/v1/registro-farmacologico/{ingreso_id}/seguimiento")
    assert r.status_code == 200
