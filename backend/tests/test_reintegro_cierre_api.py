"""Tests de integración — CEPA-042: Reintegro y cierre del caso."""


def _caso_con_reca(as_admin) -> int:
    """Crea ingreso, caso de reintegro y RECA; devuelve caso_id."""
    ing = as_admin.post(
        "/api/v1/ingresos",
        json={
            "rut": "14.963.452-5",
            "nombre": "Pedro Soto",
            "sexo": "M",
            "edad": 45,
            "region": "Biobío",
            "diagnostico": "DIAT rodilla",
            "tipo_derivacion": "DIAT",
            "tipo_ingreso": "convenio",
            "modelo_tratamiento": "ambulatorio",
            "fecha_ingreso": "2026-04-01",
        },
    )
    assert ing.status_code == 201
    caso = as_admin.post(
        "/api/v1/reintegros",
        json={
            "ingreso_id": ing.json()["id"],
            "rut": "14.963.452-5",
            "nombre": "Pedro Soto",
            "tipo_derivacion": "DIAT",
            "fecha_caso": "2026-04-01",
            "sexo": "M",
            "edad": 45,
            "region": "Biobío",
        },
    )
    assert caso.status_code == 201
    caso_id = caso.json()["id"]
    reca = as_admin.post(
        f"/api/v1/reintegros/{caso_id}/reca",
        json={
            "fecha_reca": "2026-04-05",
            "tipo_reca": "AT",
            "numero_reca": "2026-AT-001",
            "razon_social": "Empresa SA",
            "solicita_medidas": False,
        },
    )
    assert reca.status_code == 201
    return caso_id


# TC-042-01: reintegro total con todo completo → caso cerrado
def test_reintegro_total_cierre_exitoso(as_admin):
    caso_id = _caso_con_reca(as_admin)
    r = as_admin.patch(
        f"/api/v1/reintegros/{caso_id}/cierre",
        json={
            "estado_reintegro": "total",
            "fecha_reintegro": "2026-05-30",
            "remitido_isl": True,
            "alta_medica": True,
            "fecha_alta_medica": "2026-05-28",
            "alta_psicologica": False,
            "tipo_alta": "terapeutica",
            "observaciones": "Alta sin restricciones",
        },
    )
    assert r.status_code == 200, r.text
    cuerpo = r.json()
    assert cuerpo["estado_reintegro"] == "total"
    assert cuerpo["remitido_isl"] is True
    assert cuerpo["tipo_alta"] == "terapeutica"


# TC-042-01 (bis): estado reflejado en GET y auditor puede leer
def test_cierre_total_visible_por_auditor(as_admin, as_auditor):
    caso_id = _caso_con_reca(as_admin)
    as_admin.patch(
        f"/api/v1/reintegros/{caso_id}/cierre",
        json={
            "estado_reintegro": "total",
            "fecha_reintegro": "2026-05-30",
            "alta_medica": True,
            "tipo_alta": "terapeutica",
        },
    )
    r = as_auditor.get(f"/api/v1/reintegros/{caso_id}")
    assert r.status_code == 200
    assert r.json()["estado_reintegro"] == "total"


# TC-042-02: reintegro parcial sin fecha → guardado, caso abierto
def test_reintegro_parcial_sin_fecha(as_admin):
    caso_id = _caso_con_reca(as_admin)
    r = as_admin.patch(
        f"/api/v1/reintegros/{caso_id}/cierre",
        json={"estado_reintegro": "parcial"},
    )
    assert r.status_code == 200
    assert r.json()["estado_reintegro"] == "parcial"
    assert r.json()["fecha_reintegro"] is None


# TC-042-03: estado=total sin fecha_reintegro → 422
def test_total_sin_fecha_rechazado(as_admin):
    caso_id = _caso_con_reca(as_admin)
    r = as_admin.patch(
        f"/api/v1/reintegros/{caso_id}/cierre",
        json={
            "estado_reintegro": "total",
            "alta_medica": True,
            "tipo_alta": "terapeutica",
        },
    )
    assert r.status_code == 422


# TC-042-04: fecha_reintegro anterior a fecha_reca → 422
def test_fecha_reintegro_anterior_a_reca_rechazado(as_admin):
    caso_id = _caso_con_reca(as_admin)
    # fecha_reca = 2026-04-05 (creada en _caso_con_reca)
    r = as_admin.patch(
        f"/api/v1/reintegros/{caso_id}/cierre",
        json={
            "estado_reintegro": "total",
            "fecha_reintegro": "2026-03-15",  # anterior a fecha_reca 2026-04-05
            "alta_medica": True,
            "tipo_alta": "terapeutica",
        },
    )
    assert r.status_code == 422


# TC-042-05: reintegro total sin alta ni tipo_alta → 422
def test_total_sin_alta_rechazado(as_admin):
    caso_id = _caso_con_reca(as_admin)
    r = as_admin.patch(
        f"/api/v1/reintegros/{caso_id}/cierre",
        json={
            "estado_reintegro": "total",
            "fecha_reintegro": "2026-05-30",
            "alta_medica": False,
            "alta_psicologica": False,
        },
    )
    assert r.status_code == 422


# TC-042-06: Auditor no puede modificar estado de reintegro → 403
def test_auditor_no_puede_cerrar(as_auditor):
    r = as_auditor.patch(
        "/api/v1/reintegros/1/cierre",
        json={"estado_reintegro": "total", "fecha_reintegro": "2026-05-30",
              "alta_medica": True, "tipo_alta": "terapeutica"},
    )
    assert r.status_code == 403


# remitido_isl=True → queda disponible para reporte
def test_remitido_isl_persiste(as_admin):
    caso_id = _caso_con_reca(as_admin)
    as_admin.patch(
        f"/api/v1/reintegros/{caso_id}/cierre",
        json={
            "estado_reintegro": "total",
            "fecha_reintegro": "2026-05-30",
            "remitido_isl": True,
            "alta_medica": True,
            "tipo_alta": "medica",
        },
    )
    r = as_admin.get(f"/api/v1/reintegros/{caso_id}")
    assert r.json()["remitido_isl"] is True
